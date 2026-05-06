param(
    [string]$WorkspaceRoot = "F:\AGENT"
)

$ErrorActionPreference = "Stop"

$computerName = $env:COMPUTERNAME
if (-not $computerName) {
    $computerName = "windows"
}
$hostName = $computerName.ToLowerInvariant() -replace '[^a-z0-9._-]', '-'
$outputRoot = Join-Path $WorkspaceRoot "skills\windows-agent\$hostName"
$generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$manifest = Join-Path $outputRoot "MANIFEST.md"

function Expand-AgentPath {
    param([string]$RawPath)

    $path = $RawPath.Trim()
    if (-not $path) {
        return $null
    }

    if ($path -eq "~") {
        return $HOME
    }
    if ($path.StartsWith("~/") -or $path.StartsWith("~\")) {
        return Join-Path $HOME $path.Substring(2)
    }
    if ($path.StartsWith('$HOME/')) {
        return Join-Path $HOME $path.Substring(6)
    }
    if ($path.StartsWith('$HOME\')) {
        return Join-Path $HOME $path.Substring(6)
    }

    return $path
}

function Add-ConfiguredRoots {
    param(
        [string]$ConfigPath,
        [System.Collections.Generic.List[string]]$Roots
    )

    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        return
    }

    foreach ($line in Get-Content -LiteralPath $ConfigPath) {
        $clean = ($line -replace '#.*$', '').Trim()
        if (-not $clean) {
            continue
        }
        $expanded = Expand-AgentPath $clean
        if ($expanded) {
            $Roots.Add($expanded)
        }
    }
}

function Get-SafePathSegment {
    param([string]$Value)
    return ($Value -replace '^[A-Za-z]:', '$0' -replace '[\\/:*?"<>| ]+', '__' -replace '[^A-Za-z0-9._-]', '_')
}

function Copy-SkillDirectory {
    param(
        [System.IO.DirectoryInfo]$SkillDirectory,
        [string]$Root
    )

    $skillName = $SkillDirectory.Name
    if ($skillName -in @(".system", ".cache", "cache", "tmp", "node_modules", ".git", "__pycache__")) {
        return $false
    }

    $hasSkillFile = (Test-Path -LiteralPath (Join-Path $SkillDirectory.FullName "SKILL.md")) -or
        (Test-Path -LiteralPath (Join-Path $SkillDirectory.FullName "DESCRIPTION.md"))
    if (-not $hasSkillFile) {
        return $false
    }

    $displayRoot = $Root
    if ($displayRoot.StartsWith($HOME)) {
        $displayRoot = "~" + $displayRoot.Substring($HOME.Length)
    }
    $safeRoot = Get-SafePathSegment $displayRoot
    $destination = Join-Path $outputRoot (Join-Path $safeRoot $skillName)

    if (Test-Path -LiteralPath $destination) {
        Remove-Item -LiteralPath $destination -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $destination | Out-Null

    robocopy $SkillDirectory.FullName $destination /E /NFL /NDL /NJH /NJS /NP /XD .git node_modules __pycache__ /XF .DS_Store *.log *.tmp .env .env.* auth.json *.key *.pem | Out-Null
    $exitCode = $LASTEXITCODE
    if ($exitCode -ge 8) {
        throw "robocopy failed for $($SkillDirectory.FullName) with exit code $exitCode"
    }

    Add-Content -LiteralPath $manifest -Encoding UTF8 -Value "- ``$displayRoot\$skillName`` -> ``$safeRoot\$skillName``"
    Write-Host "Collected original Windows AGENT skill: $displayRoot\$skillName"
    return $true
}

$roots = [System.Collections.Generic.List[string]]::new()

# Always include the local AGENT workspace skill roots. Host-specific config can add more.
$roots.Add((Join-Path $WorkspaceRoot ".agents\skills"))
$roots.Add((Join-Path $HOME ".agents\skills"))

Add-ConfiguredRoots -ConfigPath (Join-Path $WorkspaceRoot "config\agent-skill-roots.txt") -Roots $roots
Add-ConfiguredRoots -ConfigPath (Join-Path $WorkspaceRoot "config\agent-skill-roots.$hostName.txt") -Roots $roots

$uniqueRoots = $roots | Where-Object { $_ } | Select-Object -Unique

if (Test-Path -LiteralPath $outputRoot) {
    Remove-Item -LiteralPath $outputRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

@(
    "# Windows Original AGENT Skills",
    "",
    "Host: ``$hostName``",
    "",
    "Generated at: ``$generatedAt``",
    "",
    "These are copied from original AGENT skill folders on this Windows machine.",
    "They are not rewritten as Codex-only skills.",
    "",
    "## Scanned Roots",
    ""
) | Set-Content -LiteralPath $manifest -Encoding UTF8

foreach ($root in $uniqueRoots) {
    if (Test-Path -LiteralPath $root) {
        Add-Content -LiteralPath $manifest -Encoding UTF8 -Value "- ``$root``"
    } else {
        Add-Content -LiteralPath $manifest -Encoding UTF8 -Value "- ``$root`` (missing, skipped)"
    }
}

Add-Content -LiteralPath $manifest -Encoding UTF8 -Value ""
Add-Content -LiteralPath $manifest -Encoding UTF8 -Value "## Copied Skills"
Add-Content -LiteralPath $manifest -Encoding UTF8 -Value ""

$copied = 0
foreach ($root in $uniqueRoots) {
    if (-not (Test-Path -LiteralPath $root)) {
        continue
    }
    foreach ($skillDir in Get-ChildItem -LiteralPath $root -Directory -Force) {
        if (Copy-SkillDirectory -SkillDirectory $skillDir -Root $root) {
            $copied++
        }
    }
}

if ($copied -eq 0) {
    Add-Content -LiteralPath $manifest -Encoding UTF8 -Value "_No original Windows AGENT skills found._"
}

$secretPattern = 'sk-or-v1-[A-Za-z0-9_-]{40,}|sk-ant-[A-Za-z0-9_-]{40,}|OPENAI_API_KEY\s*=\s*["'']?sk-[A-Za-z0-9_-]{20,}|ANTHROPIC_API_KEY\s*=\s*["'']?sk-[A-Za-z0-9_-]{20,}|TELEGRAM_BOT_TOKEN\s*=\s*["'']?[0-9]{8,}:[A-Za-z0-9_-]{20,}|BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY'
$matches = Get-ChildItem -LiteralPath $outputRoot -Recurse -File -Force |
    Select-String -Pattern $secretPattern -ErrorAction SilentlyContinue

if ($matches) {
    Write-Error "Potential secret-like content found in copied Windows AGENT skills. Review before pushing:`n$($matches | Out-String)"
    exit 2
}

Write-Host "Windows AGENT skill collection complete. Copied $copied skill(s) into $outputRoot"

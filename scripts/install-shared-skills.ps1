param(
    [switch]$SkipHermes,
    [switch]$SkipCodex
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "F:\AGENT"
$skillsRoot = Join-Path $workspaceRoot "skills\shared"
$distro = "Ubuntu-24.04"

if (-not (Test-Path $skillsRoot)) {
    throw "Shared skills folder not found: $skillsRoot"
}

$skills = Get-ChildItem -Directory -Path $skillsRoot

if (-not $SkipCodex) {
    $codexSkillsRoot = "C:\Users\User\.codex\skills"
    New-Item -ItemType Directory -Force -Path $codexSkillsRoot | Out-Null
    foreach ($skill in $skills) {
        $target = Join-Path $codexSkillsRoot $skill.Name
        if (Test-Path $target) {
            Remove-Item -LiteralPath $target -Recurse -Force
        }
        Copy-Item -LiteralPath $skill.FullName -Destination $target -Recurse -Force
        Write-Host "Installed Codex skill: $($skill.Name)"
    }
}

if (-not $SkipHermes) {
    wsl.exe -d $distro -- bash -lc "mkdir -p /root/.hermes/skills/shared && rm -rf /root/.hermes/skills/shared/* && cp -a /mnt/f/AGENT/skills/shared/. /root/.hermes/skills/shared/"
    Write-Host "Installed Hermes shared skills under /root/.hermes/skills/shared"
}

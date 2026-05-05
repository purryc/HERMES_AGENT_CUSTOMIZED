param(
    [string]$RemoteUrl = "https://github.com/purryc/hermes-memory.git",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$sourceRoot = "F:\AGENT"
$mirrorRoot = Join-Path $sourceRoot ".memory-git"

if (-not (Test-Path $mirrorRoot)) {
    git clone $RemoteUrl $mirrorRoot
}

Push-Location $mirrorRoot
try {
    git remote set-url origin $RemoteUrl
    git fetch origin --prune
    $remoteBranch = git ls-remote --heads origin $Branch
    if (-not $remoteBranch) {
        throw "Remote branch '$Branch' does not exist yet. Push from one machine first."
    }
    $existingBranch = git branch --list $Branch
    if ($existingBranch) {
        git checkout $Branch
    } else {
        git checkout -b $Branch "origin/$Branch"
    }
    git pull --ff-only origin $Branch
} finally {
    Pop-Location
}

$allowedFiles = @(
    "AGENTS.md",
    "memory/SHARED_AGENT_MEMORY.md",
    "memory/mac-codex-memory.md",
    "docs/mac-codex-memory-sync.md",
    "docs/git-memory-skills-sync.md",
    "specs/002-dashboard-companion-chat/plan.md",
    "skills/shared",
    "skills/mac-codex",
    "scripts/export-mac-codex-memory.sh",
    "scripts/install-mac-codex-memory-sync.sh",
    "scripts/uninstall-mac-codex-memory-sync.sh",
    "scripts/install-shared-skills.ps1",
    "scripts/install-shared-skills.sh",
    "scripts/sync-windows-to-github.ps1",
    "scripts/install-windows-github-memory-sync-task.ps1",
    "scripts/uninstall-windows-github-memory-sync-task.ps1",
    "scripts/push-memory-github.ps1",
    "scripts/pull-memory-github.ps1",
    "scripts/push-memory-github.sh",
    "scripts/pull-memory-github.sh",
    "scripts/collect-mac-codex-state.sh",
    "scripts/sync-mac-from-github.sh",
    "scripts/sync-mac-to-github.sh"
)

foreach ($relative in $allowedFiles) {
    $src = Join-Path $mirrorRoot $relative
    $dst = Join-Path $sourceRoot $relative
    if (Test-Path $src) {
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        if (Test-Path $dst) {
            Remove-Item -LiteralPath $dst -Recurse -Force
        }
        Copy-Item -LiteralPath $src -Destination $dst -Force -Recurse
        Write-Host "Updated $relative"
    }
}

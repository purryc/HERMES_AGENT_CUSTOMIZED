param(
    [string]$RemoteUrl = "https://github.com/purryc/hermes-memory.git",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$sourceRoot = "F:\AGENT"
$mirrorRoot = Join-Path $sourceRoot ".memory-git"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"

$allowedFiles = @(
    "AGENTS.md",
    "README.md",
    ".gitignore",
    "memory/SHARED_AGENT_MEMORY.md",
    "memory/mac-codex-memory.md",
    "docs/mac-codex-memory-sync.md",
    "docs/git-memory-skills-sync.md",
    "docs/mac-agent-skill-sync.md",
    "config/agent-skill-roots.example.txt",
    "config/agent-skill-roots.txt",
    "config/project-agent-roots.example.txt",
    "config/project-agent-roots.txt",
    "specs/002-dashboard-companion-chat/plan.md",
    "project-agents",
    "skills/shared",
    "skills/windows-agent",
    "skills/mac-agent",
    "skills/mac-codex",
    "scripts/export-hermes-memory.sh",
    "scripts/sync-agent-memory.ps1",
    "scripts/install-agent-memory-sync-task.ps1",
    "scripts/uninstall-agent-memory-sync-task.ps1",
    "scripts/sync-windows-to-github.ps1",
    "scripts/install-windows-github-memory-sync-task.ps1",
    "scripts/uninstall-windows-github-memory-sync-task.ps1",
    "scripts/collect-windows-agent-state.ps1",
    "scripts/export-mac-codex-memory.sh",
    "scripts/install-mac-codex-memory-sync.sh",
    "scripts/uninstall-mac-codex-memory-sync.sh",
    "scripts/install-shared-skills.ps1",
    "scripts/install-shared-skills.sh",
    "scripts/push-memory-github.ps1",
    "scripts/pull-memory-github.ps1",
    "scripts/push-memory-github.sh",
    "scripts/pull-memory-github.sh",
    "scripts/collect-mac-agent-state.sh",
    "scripts/collect-mac-codex-state.sh",
    "scripts/sync-mac-from-github.sh",
    "scripts/sync-mac-to-github.sh",
    "scripts/sync-project-agents.sh"
)

if (-not (Test-Path $mirrorRoot)) {
    git clone $RemoteUrl $mirrorRoot
}

Push-Location $mirrorRoot
try {
    git remote set-url origin $RemoteUrl
    git fetch origin --prune
    $existingBranch = git branch --list $Branch
    if ($existingBranch) {
        git checkout $Branch
    } else {
        git checkout -b $Branch
    }
    $remoteBranch = git ls-remote --heads origin $Branch
    if ($remoteBranch) {
        git pull --ff-only origin $Branch
    }
} finally {
    Pop-Location
}

foreach ($relative in $allowedFiles) {
    $src = Join-Path $sourceRoot $relative
    $dst = Join-Path $mirrorRoot $relative
    if (Test-Path $src) {
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        if (Test-Path $dst) {
            Remove-Item -LiteralPath $dst -Recurse -Force
        }
        Copy-Item -LiteralPath $src -Destination $dst -Force -Recurse
    }
}

$mirrorGitignore = Join-Path $mirrorRoot ".gitignore"
@"
memory/hermes-raw-memory-export.md
memory/mac-codex-raw-memory-export.md
memory/mac-codex-sync.log
memory/mac-codex-sync.err.log
memory/*.tmp
memory/encrypted/
keys/
*.env
.env
.env.*
auth.json
*.key
*.pem
.secrets/
*.identity.txt
.tmp-project-agents.*
"@ | Set-Content -LiteralPath $mirrorGitignore -Encoding UTF8

Push-Location $mirrorRoot
try {
    if (-not (git config user.name)) {
        git config user.name "shino yan"
    }
    if (-not (git config user.email)) {
        git config user.email "memory-sync@local"
    }
    git add --all
    $changes = git status --porcelain
    if (-not $changes) {
        Write-Host "No shared-memory changes to push."
        exit 0
    }

    git commit -m "Sync shared agent memory ($stamp)"
    git push -u origin $Branch
} finally {
    Pop-Location
}

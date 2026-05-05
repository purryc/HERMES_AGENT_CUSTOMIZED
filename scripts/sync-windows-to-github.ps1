param(
    [switch]$ExportHermesRaw
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "F:\AGENT"
$syncScript = Join-Path $workspaceRoot "scripts\sync-agent-memory.ps1"
$pushScript = Join-Path $workspaceRoot "scripts\push-memory-github.ps1"

if ($ExportHermesRaw) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $syncScript -ExportHermesRaw
}

# push-memory-github.ps1 only copies allowlisted shared files into .memory-git.
# Raw memory exports, auth files, .env files, keys, and tokens remain excluded.
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $pushScript

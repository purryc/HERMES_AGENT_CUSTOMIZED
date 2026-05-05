param(
    [switch]$Status,
    [switch]$ExportHermesRaw
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "F:\AGENT"
$sharedMemory = Join-Path $workspaceRoot "memory\SHARED_AGENT_MEMORY.md"
$rawExport = Join-Path $workspaceRoot "memory\hermes-raw-memory-export.md"
$distro = "Ubuntu-24.04"

if (-not (Test-Path $sharedMemory)) {
    throw "Shared memory file not found: $sharedMemory"
}

if ($ExportHermesRaw) {
    $generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
    wsl.exe -d $distro -- bash -lc "chmod +x /mnt/f/AGENT/scripts/export-hermes-memory.sh && /mnt/f/AGENT/scripts/export-hermes-memory.sh '$generatedAt'"
    Write-Host "Exported Hermes raw memory to $rawExport"
    exit 0
}

Write-Host "Shared memory: $sharedMemory"
Write-Host "Hermes WSL path: /mnt/f/AGENT/memory/SHARED_AGENT_MEMORY.md"
Write-Host "Raw export: $rawExport"
if (Test-Path $rawExport) {
    $item = Get-Item $rawExport
    Write-Host "Raw export last updated: $($item.LastWriteTime)"
} else {
    Write-Host "Raw export last updated: never"
}
Write-Host ""
Write-Host "Use -ExportHermesRaw only when you intentionally want a local raw export of Hermes memory."

$ErrorActionPreference = "Stop"

$taskName = "HermesCodexMemorySync"

schtasks.exe /Delete /TN $taskName /F | Out-Host
Write-Host "Removed scheduled task: $taskName"

$ErrorActionPreference = "Stop"

$taskName = "HermesGitHubMemoryDailySync"

schtasks.exe /Delete /TN $taskName /F | Out-Host
Write-Host "Uninstalled scheduled task: $taskName"

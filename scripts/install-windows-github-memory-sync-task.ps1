param(
    [string]$At = "23:55"
)

$ErrorActionPreference = "Stop"

$taskName = "HermesGitHubMemoryDailySync"
$scriptPath = "F:\AGENT\scripts\sync-windows-to-github.ps1"

if (-not (Test-Path $scriptPath)) {
    throw "Sync script not found: $scriptPath"
}

$taskCommand = "powershell.exe"
$taskArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -ExportHermesRaw"

schtasks.exe /Create `
    /TN $taskName `
    /SC DAILY `
    /ST $At `
    /TR "`"$taskCommand`" $taskArgs" `
    /F | Out-Host

Write-Host "Installed scheduled task: $taskName"
Write-Host "Schedule: daily at $At"
Write-Host "Command: $taskCommand $taskArgs"
Write-Host "GitHub push uses the safe allowlist in scripts\push-memory-github.ps1."

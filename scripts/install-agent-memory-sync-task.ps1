param(
    [int]$IntervalMinutes = 30
)

$ErrorActionPreference = "Stop"

$taskName = "HermesCodexMemorySync"
$scriptPath = "F:\AGENT\scripts\sync-agent-memory.ps1"

if (-not (Test-Path $scriptPath)) {
    throw "Sync script not found: $scriptPath"
}

$taskCommand = "powershell.exe"
$taskArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -ExportHermesRaw"

schtasks.exe /Create `
    /TN $taskName `
    /SC MINUTE `
    /MO $IntervalMinutes `
    /TR "`"$taskCommand`" $taskArgs" `
    /F | Out-Host

Write-Host "Installed scheduled task: $taskName"
Write-Host "Interval: every $IntervalMinutes minute(s)"
Write-Host "Command: $taskCommand $taskArgs"

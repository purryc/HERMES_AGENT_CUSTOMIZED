$ErrorActionPreference = "Stop"

$taskName = "HermesGatewayAutostart"
$scriptPath = "F:\AGENT\scripts\start-hermes-gateway.ps1"
$powershellPath = (Get-Command powershell.exe).Source
$action = New-ScheduledTaskAction -Execute $powershellPath -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable

Register-ScheduledTask `
  -TaskName $taskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Start Hermes gateway in WSL at Windows logon" `
  -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Write-Output "Installed and started scheduled task: $taskName"

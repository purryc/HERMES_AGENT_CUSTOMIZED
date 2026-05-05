param(
    [string]$WorkspaceRoot = "F:\AGENT"
)

$ErrorActionPreference = "Stop"

$statePath = Join-Path $WorkspaceRoot "data\hermes-remote-tunnel.json"
if (-not (Test-Path $statePath)) {
    Write-Host "No Hermes remote tunnel state found at $statePath"
    return
}

$state = Get-Content $statePath -Raw | ConvertFrom-Json
foreach ($pid in @($state.cloudflared_pid, $state.guard_pid)) {
    if ($pid) {
        Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue
    }
}

Remove-Item $statePath -Force -ErrorAction SilentlyContinue
Write-Host "Hermes remote tunnel stopped."

param(
    [string]$WorkspaceRoot = "F:\AGENT",
    [string]$RemoteDashboardUrl = "https://remote-dashboard-six.vercel.app",
    [switch]$SkipVercelDeploy
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

$dashboardScript = Join-Path $WorkspaceRoot "scripts\start-hermes-dashboard.ps1"
$tunnelScript = Join-Path $WorkspaceRoot "scripts\start-hermes-cloudflare-tunnel.ps1"
$statePath = Join-Path $WorkspaceRoot "data\hermes-remote-tunnel.json"
$tokenPath = Join-Path $WorkspaceRoot "data\hermes-remote-dashboard-token.txt"
$remoteDashboardRoot = Join-Path $WorkspaceRoot "remote-dashboard"

Write-Step "Starting local Hermes Dashboard"
Start-Process powershell.exe -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-WindowStyle", "Hidden",
    "-File", "`"$dashboardScript`""
) -WorkingDirectory $WorkspaceRoot

Start-Sleep -Seconds 3

Write-Step "Starting protected Cloudflare tunnel"
& $tunnelScript -WorkspaceRoot $WorkspaceRoot

$token = (Get-Content $tokenPath -Raw).Trim()
$state = Get-Content $statePath -Raw | ConvertFrom-Json
$tunnelUrl = [string]$state.tunnel_url

if (-not $token) {
    throw "Remote dashboard token was not created at $tokenPath"
}
if (-not $tunnelUrl) {
    throw "Cloudflare tunnel URL was not created at $statePath"
}

if (-not $SkipVercelDeploy) {
    Write-Step "Updating Vercel production deployment with the current tunnel URL"
    Push-Location $remoteDashboardRoot
    try {
        npx.cmd vercel --yes --prod --env "HERMES_TUNNEL_URL=$tunnelUrl" --env "REMOTE_DASHBOARD_TOKEN=$token"
    } finally {
        Pop-Location
    }
}

Write-Step "Verifying remote dashboard can reach local Hermes"
Invoke-RestMethod "$RemoteDashboardUrl/api/hermes?path=%2Fhealthz" -Headers @{
    "X-Remote-Dashboard-Token" = $token
} | Out-Null

Set-Clipboard -Value $token
Start-Process $RemoteDashboardUrl

Write-Host ""
Write-Host "Hermes Remote Dashboard is ready." -ForegroundColor Green
Write-Host "Remote URL: $RemoteDashboardUrl"
Write-Host "Token copied to clipboard. Paste it into REMOTE TOKEN, then click CHECK HEALTH."
Write-Host ""
Read-Host "Press Enter to close this window"

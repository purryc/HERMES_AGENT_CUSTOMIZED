param(
    [string]$WorkspaceRoot = "F:\AGENT",
    [string]$HermesUrl = "http://127.0.0.1:8787",
    [string]$GuardHost = "127.0.0.1",
    [int]$GuardPort = 8790,
    [string]$RemoteToken = "",
    [int]$TimeoutSeconds = 45
)

$ErrorActionPreference = "Stop"

$dataDir = Join-Path $WorkspaceRoot "data"
$statePath = Join-Path $dataDir "hermes-remote-tunnel.json"
$tokenPath = Join-Path $dataDir "hermes-remote-dashboard-token.txt"
$guardOut = Join-Path $dataDir "hermes-tunnel-guard.out.log"
$guardErr = Join-Path $dataDir "hermes-tunnel-guard.err.log"
$cloudflaredOut = Join-Path $dataDir "cloudflared-hermes.out.log"
$cloudflaredErr = Join-Path $dataDir "cloudflared-hermes.err.log"
$guardUrl = "http://${GuardHost}:${GuardPort}"

New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

try {
    $health = Invoke-RestMethod -Uri "$HermesUrl/healthz" -TimeoutSec 5
    if (-not $health.ok) {
        throw "Hermes health returned ok=false"
    }
} catch {
    throw "Local Hermes is not healthy at $HermesUrl. Start it before opening a remote tunnel. $($_.Exception.Message)"
}

$cloudflared = (Get-Command cloudflared -ErrorAction Stop).Source

if (-not $RemoteToken) {
    if (Test-Path $tokenPath) {
        $RemoteToken = (Get-Content $tokenPath -Raw).Trim()
    }
    if (-not $RemoteToken) {
        $bytes = New-Object byte[] 32
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $rng.GetBytes($bytes)
        } finally {
            $rng.Dispose()
        }
        $RemoteToken = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
        Set-Content -Path $tokenPath -Value $RemoteToken -Encoding ascii
    }
}

if (Test-Path $statePath) {
    try {
        $existing = Get-Content $statePath -Raw | ConvertFrom-Json
        foreach ($pid in @($existing.guard_pid, $existing.cloudflared_pid)) {
            if ($pid) {
                Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Warning "Could not stop previous tunnel state: $($_.Exception.Message)"
    }
}

Remove-Item $guardOut, $guardErr, $cloudflaredOut, $cloudflaredErr -Force -ErrorAction SilentlyContinue

$python = (Get-Command py -ErrorAction Stop).Source
$guardArgs = @(
    "-3.10",
    (Join-Path $WorkspaceRoot "scripts\hermes_tunnel_guard.py"),
    "--host", $GuardHost,
    "--port", "$GuardPort",
    "--target", $HermesUrl,
    "--token", $RemoteToken,
    "--timeout-seconds", "$TimeoutSeconds"
)
$guardProcess = Start-Process -FilePath $python -ArgumentList $guardArgs -WorkingDirectory $WorkspaceRoot -RedirectStandardOutput $guardOut -RedirectStandardError $guardErr -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 1

try {
    Invoke-RestMethod -Uri "$guardUrl/healthz" -Headers @{ "X-Hermes-Remote-Token" = $RemoteToken } -TimeoutSec 5 | Out-Null
} catch {
    Stop-Process -Id $guardProcess.Id -Force -ErrorAction SilentlyContinue
    throw "Tunnel guard did not become healthy at $guardUrl. $($_.Exception.Message)"
}

$cloudflaredProcess = Start-Process -FilePath $cloudflared -ArgumentList @("tunnel", "--url", $guardUrl) -WorkingDirectory $WorkspaceRoot -RedirectStandardOutput $cloudflaredOut -RedirectStandardError $cloudflaredErr -WindowStyle Hidden -PassThru

$deadline = (Get-Date).AddSeconds(35)
$tunnelUrl = ""
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    $logs = ""
    foreach ($path in @($cloudflaredOut, $cloudflaredErr)) {
        if (Test-Path $path) {
            $logs += "`n" + (Get-Content $path -Raw)
        }
    }
    $match = [regex]::Match($logs, "https://[-a-zA-Z0-9]+\.trycloudflare\.com")
    if ($match.Success) {
        $tunnelUrl = $match.Value
        break
    }
}

if (-not $tunnelUrl) {
    Stop-Process -Id $guardProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $cloudflaredProcess.Id -Force -ErrorAction SilentlyContinue
    throw "Cloudflare tunnel did not report a trycloudflare URL. Check $cloudflaredErr"
}

$state = [ordered]@{
    guard_pid = $guardProcess.Id
    cloudflared_pid = $cloudflaredProcess.Id
    local_guard_url = $guardUrl
    target_url = $HermesUrl
    tunnel_url = $tunnelUrl
    token_path = $tokenPath
    started_at = (Get-Date).ToString("o")
}
$state | ConvertTo-Json | Set-Content -Path $statePath -Encoding utf8

Write-Host ""
Write-Host "Hermes remote tunnel is ready." -ForegroundColor Green
Write-Host "HERMES_TUNNEL_URL=$tunnelUrl"
Write-Host "REMOTE_DASHBOARD_TOKEN=$RemoteToken"
Write-Host ""
Write-Host "Set these two variables in Vercel for the remote-dashboard project."
Write-Host "State: $statePath"

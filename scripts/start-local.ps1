param(
    [string]$ConfigPath = "F:\AGENT\config\agent.example.json",
    [string]$Host = "127.0.0.1",
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

Write-Host "Starting Hermes Personal Work Agent..." -ForegroundColor Cyan
Write-Host "Config: $ConfigPath"
Write-Host "Host:   $Host"
Write-Host "Port:   $Port"

if (-not (Test-Path "F:\AGENT\.env")) {
    Write-Warning "F:\AGENT\.env not found. Copy .env.example to .env and set OPENROUTER_API_KEY if you want real model responses."
}

py -3.10 -m hermes_personal_agent.cli serve --config $ConfigPath --host $Host --port $Port

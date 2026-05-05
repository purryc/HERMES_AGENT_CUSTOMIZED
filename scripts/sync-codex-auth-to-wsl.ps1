$ErrorActionPreference = "Stop"

$windowsAuth = "C:\Users\User\.codex\auth.json"
$wslAuth = "\\wsl.localhost\Ubuntu-24.04\root\.codex\auth.json"
$distro = "Ubuntu-24.04"

if (-not (Test-Path $windowsAuth)) {
    throw "Windows Codex auth file not found: $windowsAuth"
}

Copy-Item -LiteralPath $windowsAuth -Destination $wslAuth -Force
wsl.exe -d $distro -- bash -lc "chmod 600 /root/.codex/auth.json /root/.codex/config.toml"

Write-Host "Copied Windows Codex ChatGPT auth into WSL root Codex."
Write-Host "WSL Codex should now work for Hermes terminal calls."

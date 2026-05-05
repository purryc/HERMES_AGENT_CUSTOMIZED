param(
    [string]$Label = "windows-hermes-codex"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "F:\AGENT"
$distro = "Ubuntu-24.04"
wsl.exe -d $distro -- bash -lc "chmod +x /mnt/f/AGENT/scripts/decrypt-raw-memory-wsl.sh && /mnt/f/AGENT/scripts/decrypt-raw-memory-wsl.sh '$Label'"

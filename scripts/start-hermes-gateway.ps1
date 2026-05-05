$ErrorActionPreference = "Stop"

$workspaceRoot = "F:\AGENT"
$wslScriptPath = "/mnt/f/AGENT/scripts/restart-hermes-gateway.sh"
$distro = "Ubuntu-24.04"

wsl.exe -d $distro -- bash -lc "chmod +x $wslScriptPath && $wslScriptPath"

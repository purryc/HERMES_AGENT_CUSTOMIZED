$ErrorActionPreference = "Stop"

$distro = "Ubuntu-24.04"
$dashboardUrl = "http://127.0.0.1:9119"
$wslScriptPath = "/mnt/f/AGENT/scripts/start-hermes-dashboard.sh"

wsl.exe -d $distro -- bash -lc "chmod +x $wslScriptPath && $wslScriptPath"
Start-Process $dashboardUrl

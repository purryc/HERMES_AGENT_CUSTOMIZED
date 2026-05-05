$ErrorActionPreference = "Stop"

$distro = "Ubuntu-24.04"

wsl.exe -d $distro -- bash -lc "ps -ef | grep '[h]ermes gateway' || true; echo '---'; /root/.local/bin/hermes gateway status || true; echo '---'; tmux list-sessions 2>/dev/null || true"

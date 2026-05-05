$ErrorActionPreference = "Stop"

$distro = "Ubuntu-24.04"

wsl.exe -d $distro -- bash -lc "ps -ef | grep '[h]ermes dashboard' || true; echo '---'; ss -ltnp | grep ':9119' || true; echo '---'; tmux list-sessions 2>/dev/null | grep 'hermes-dashboard' || true; echo '---'; PYTHONPATH=/root/.hermes/hermes-agent /root/.local/bin/hermes --version"

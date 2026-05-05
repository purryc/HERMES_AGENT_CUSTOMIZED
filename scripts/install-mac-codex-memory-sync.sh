#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/.." && pwd)"
export_script="${workspace_root}/scripts/export-mac-codex-memory.sh"
shared_memory="${workspace_root}/memory/SHARED_AGENT_MEMORY.md"
launch_agents="${HOME}/Library/LaunchAgents"
plist="${launch_agents}/com.shino.agent-memory-sync.plist"

if [ ! -f "${shared_memory}" ]; then
  printf 'Shared memory file not found: %s\n' "${shared_memory}" >&2
  exit 1
fi

chmod +x "${export_script}"
mkdir -p "${HOME}/.codex/memories" "${launch_agents}"
ln -sf "${shared_memory}" "${HOME}/.codex/memories/shared-agent-memory.md"

cat > "${plist}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.shino.agent-memory-sync</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${export_script}</string>
  </array>
  <key>StartInterval</key>
  <integer>1800</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${workspace_root}/memory/mac-codex-sync.log</string>
  <key>StandardErrorPath</key>
  <string>${workspace_root}/memory/mac-codex-sync.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)" "${plist}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${plist}"
launchctl kickstart -k "gui/$(id -u)/com.shino.agent-memory-sync"

"${export_script}"

printf '\nInstalled Mac Codex memory sync.\n'
printf 'Shared memory symlink: %s\n' "${HOME}/.codex/memories/shared-agent-memory.md"
printf 'LaunchAgent: %s\n' "${plist}"
printf 'Runs every 30 minutes while you are logged in.\n'

#!/usr/bin/env bash
set -euo pipefail

plist="${HOME}/Library/LaunchAgents/com.shino.agent-memory-sync.plist"

launchctl bootout "gui/$(id -u)" "${plist}" >/dev/null 2>&1 || true
rm -f "${plist}"

printf 'Removed Mac Codex memory sync LaunchAgent.\n'

#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/.." && pwd)"

cd "${workspace_root}"
chmod +x scripts/*.sh
./scripts/pull-memory-github.sh
./scripts/collect-mac-agent-state.sh
./scripts/sync-project-agents.sh
./scripts/push-memory-github.sh

printf '\nMac memory, original AGENT skills, and project AGENTS.md files were collected and pushed to GitHub.\n'

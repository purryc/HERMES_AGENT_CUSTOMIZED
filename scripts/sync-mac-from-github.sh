#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/.." && pwd)"

cd "${workspace_root}"
chmod +x scripts/*.sh
./scripts/pull-memory-github.sh
./scripts/install-shared-skills.sh

printf '\nMac is up to date with shared memory and shared skills.\n'
printf 'Read AGENTS.md and memory/SHARED_AGENT_MEMORY.md before substantial work.\n'

#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf 'collect-mac-codex-state.sh is kept for compatibility.\n'
printf 'Using collect-mac-agent-state.sh so original AGENT folder skills are copied.\n\n'

exec "${script_dir}/collect-mac-agent-state.sh"

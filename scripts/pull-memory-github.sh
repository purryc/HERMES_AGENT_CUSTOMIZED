#!/usr/bin/env bash
set -euo pipefail

remote_url="${1:-https://github.com/purryc/hermes-memory.git}"
branch="${2:-main}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source_root="$(cd "${script_dir}/.." && pwd)"
mirror_root="${source_root}/.memory-git"

allowed_files=(
  "AGENTS.md"
  "memory/SHARED_AGENT_MEMORY.md"
  "memory/mac-codex-memory.md"
  "docs/mac-codex-memory-sync.md"
  "docs/git-memory-skills-sync.md"
  "specs/002-dashboard-companion-chat/plan.md"
  "skills/shared"
  "skills/mac-codex"
  "scripts/export-mac-codex-memory.sh"
  "scripts/install-mac-codex-memory-sync.sh"
  "scripts/uninstall-mac-codex-memory-sync.sh"
  "scripts/install-shared-skills.ps1"
  "scripts/install-shared-skills.sh"
  "scripts/sync-windows-to-github.ps1"
  "scripts/install-windows-github-memory-sync-task.ps1"
  "scripts/uninstall-windows-github-memory-sync-task.ps1"
  "scripts/push-memory-github.ps1"
  "scripts/pull-memory-github.ps1"
  "scripts/push-memory-github.sh"
  "scripts/pull-memory-github.sh"
  "scripts/collect-mac-codex-state.sh"
  "scripts/sync-mac-from-github.sh"
  "scripts/sync-mac-to-github.sh"
)

if [ ! -d "${mirror_root}/.git" ]; then
  git clone "${remote_url}" "${mirror_root}"
fi

git -C "${mirror_root}" remote set-url origin "${remote_url}"
git -C "${mirror_root}" fetch origin --prune
git -C "${mirror_root}" checkout "${branch}" 2>/dev/null || git -C "${mirror_root}" checkout -b "${branch}" "origin/${branch}"
git -C "${mirror_root}" pull --ff-only origin "${branch}"

for relative in "${allowed_files[@]}"; do
  src="${mirror_root}/${relative}"
  dst="${source_root}/${relative}"
  if [ -e "${src}" ]; then
    mkdir -p "$(dirname "${dst}")"
    rm -rf "${dst}"
    cp -a "${src}" "${dst}"
    printf 'Updated %s\n' "${relative}"
  fi
done

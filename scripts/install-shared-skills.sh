#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/.." && pwd)"
skills_root="${workspace_root}/skills/shared"

if [ ! -d "${skills_root}" ]; then
  printf 'Shared skills folder not found: %s\n' "${skills_root}" >&2
  exit 1
fi

mkdir -p "${HOME}/.codex/skills"
for skill_dir in "${skills_root}"/*; do
  [ -d "${skill_dir}" ] || continue
  skill_name="$(basename "${skill_dir}")"
  rm -rf "${HOME}/.codex/skills/${skill_name}"
  cp -a "${skill_dir}" "${HOME}/.codex/skills/${skill_name}"
  printf 'Installed Codex skill: %s\n' "${skill_name}"
done

if [ -d "/root/.hermes/skills" ] && [ "$(id -u)" -eq 0 ]; then
  mkdir -p /root/.hermes/skills/shared
  rm -rf /root/.hermes/skills/shared/*
  cp -a "${skills_root}/." /root/.hermes/skills/shared/
  printf 'Installed Hermes shared skills under /root/.hermes/skills/shared\n'
fi

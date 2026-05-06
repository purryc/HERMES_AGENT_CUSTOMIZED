#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/.." && pwd)"
host="$(hostname | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/-/g')"
output_root="${workspace_root}/project-agents/${host}"
tmp_root="$(mktemp -d "${workspace_root}/.tmp-project-agents.XXXXXX")"
manifest="${tmp_root}/MANIFEST.md"
count=0

cleanup() {
  rm -rf "${tmp_root}"
}
trap cleanup EXIT

expand_path() {
  local raw="$1"
  case "${raw}" in
    "~") printf '%s\n' "${HOME}" ;;
    "~/"*) printf '%s/%s\n' "${HOME}" "${raw#~/}" ;;
    "\$HOME") printf '%s\n' "${HOME}" ;;
    "\$HOME/"*) printf '%s/%s\n' "${HOME}" "${raw#\$HOME/}" ;;
    *) printf '%s\n' "${raw}" ;;
  esac
}

add_configured_roots() {
  local config_file="$1"
  [ -f "${config_file}" ] || return 0

  while IFS= read -r line || [ -n "${line}" ]; do
    line="${line%%#*}"
    line="$(printf '%s' "${line}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    [ -n "${line}" ] || continue
    roots+=("$(expand_path "${line}")")
  done < "${config_file}"
}

roots=()
add_configured_roots "${workspace_root}/config/project-agent-roots.txt"
add_configured_roots "${workspace_root}/config/project-agent-roots.${host}.txt"

if [ "${#roots[@]}" -eq 0 ]; then
  roots=(
    "${HOME}/Projects"
    "${HOME}/Developer"
    "${HOME}/Code"
    "${HOME}/Documents"
    "${HOME}/Desktop"
    "${HOME}/Work"
  )
fi

{
  printf '# Project AGENTS.md Index\n\n'
  printf 'Host: `%s`\n\n' "${host}"
  printf 'Generated at: `%s`\n\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
  printf 'This folder contains copied `AGENTS.md` files from configured local project roots.\n'
  printf 'It is meant for cross-machine context, not for secrets.\n\n'
  printf '## Scanned Roots\n\n'
  for root in "${roots[@]}"; do
    if [ -d "${root}" ]; then
      printf '%s\n' "- \`${root/#${HOME}/~}\`"
    else
      printf '%s\n' "- \`${root/#${HOME}/~}\` (missing, skipped)"
    fi
  done
  printf '\n## Files\n\n'
} > "${manifest}"

copy_agent_file() {
  local file="$1"
  local project_dir
  local display_dir
  local safe_dir
  local hash
  local dest_dir

  project_dir="$(cd "$(dirname "${file}")" && pwd)"
  display_dir="${project_dir/#${HOME}/~}"
  safe_dir="$(printf '%s' "${display_dir}" | sed 's/^~/HOME/; s/[^A-Za-z0-9._-]/__/g')"
  if command -v shasum >/dev/null 2>&1; then
    hash="$(printf '%s' "${project_dir}" | shasum | awk '{print substr($1,1,12)}')"
  else
    hash="$(printf '%s' "${project_dir}" | cksum | awk '{print $1}')"
  fi

  dest_dir="${tmp_root}/${safe_dir}-${hash}"
  mkdir -p "${dest_dir}"
  cp "${file}" "${dest_dir}/AGENTS.md"
  printf '%s\n' "- \`${display_dir}/AGENTS.md\` -> \`$(basename "${dest_dir}")/AGENTS.md\`" >> "${manifest}"
  count=$((count + 1))
}

for root in "${roots[@]}"; do
  [ -d "${root}" ] || continue
  while IFS= read -r file; do
    copy_agent_file "${file}"
  done < <(
    find "${root}" \
      \( -name .git -o -name .memory-git -o -name node_modules -o -name .venv -o -name venv -o -name dist -o -name build -o -name .next -o -name Library \) -prune \
      -o -type f -name AGENTS.md -print
  )
done

if [ "${count}" -eq 0 ]; then
  printf '_No AGENTS.md files found._\n' >> "${manifest}"
fi

secret_pattern='sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY|ANTHROPIC_API_KEY|TELEGRAM_BOT_TOKEN|BEGIN .*PRIVATE KEY|password[[:space:]]*=|token[[:space:]]*='
if grep -RInE "${secret_pattern}" "${tmp_root}" >/tmp/project-agents-secret-scan.txt 2>/dev/null; then
  printf 'Refusing to sync project AGENTS.md files because possible secrets were found:\n' >&2
  cat /tmp/project-agents-secret-scan.txt >&2
  rm -f /tmp/project-agents-secret-scan.txt
  exit 2
fi
rm -f /tmp/project-agents-secret-scan.txt

rm -rf "${output_root}"
mkdir -p "$(dirname "${output_root}")"
mv "${tmp_root}" "${output_root}"
trap - EXIT

printf 'Synced %s AGENTS.md file(s) into %s\n' "${count}" "${output_root}"

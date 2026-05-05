#!/usr/bin/env bash
set -euo pipefail

label="${1:-mac-codex}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/.." && pwd)"
identity_path="${workspace_root}/.secrets/age/${label}.identity.txt"

command -v age >/dev/null 2>&1 || { printf 'age is missing. Run scripts/setup-age-mac.sh first.\n' >&2; exit 1; }
test -f "${identity_path}" || { printf 'Missing identity: %s\n' "${identity_path}" >&2; exit 1; }

decrypt_one() {
  local input="$1"
  local output="$2"
  if [ -f "${input}" ]; then
    age -d -i "${identity_path}" -o "${output}.tmp" "${input}"
    mv "${output}.tmp" "${output}"
    printf 'Decrypted %s -> %s\n' "${input}" "${output}"
  else
    printf 'Skipped missing %s\n' "${input}"
  fi
}

decrypt_one "${workspace_root}/memory/encrypted/hermes-raw-memory-export.md.age" "${workspace_root}/memory/hermes-raw-memory-export.md"
decrypt_one "${workspace_root}/memory/encrypted/mac-codex-raw-memory-export.md.age" "${workspace_root}/memory/mac-codex-raw-memory-export.md"

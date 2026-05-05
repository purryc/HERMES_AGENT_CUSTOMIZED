#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/.." && pwd)"
recipients_path="${workspace_root}/keys/recipients.txt"
encrypted_dir="${workspace_root}/memory/encrypted"

command -v age >/dev/null 2>&1 || { printf 'age is missing. Run scripts/setup-age-mac.sh first.\n' >&2; exit 1; }
test -s "${recipients_path}" || { printf 'No recipients found at %s\n' "${recipients_path}" >&2; exit 1; }
mkdir -p "${encrypted_dir}"

encrypt_one() {
  local input="$1"
  local output="$2"
  if [ -f "${input}" ]; then
    age -R "${recipients_path}" -o "${output}.tmp" "${input}"
    mv "${output}.tmp" "${output}"
    printf 'Encrypted %s -> %s\n' "${input}" "${output}"
  else
    printf 'Skipped missing %s\n' "${input}"
  fi
}

encrypt_one "${workspace_root}/memory/hermes-raw-memory-export.md" "${encrypted_dir}/hermes-raw-memory-export.md.age"
encrypt_one "${workspace_root}/memory/mac-codex-raw-memory-export.md" "${encrypted_dir}/mac-codex-raw-memory-export.md.age"

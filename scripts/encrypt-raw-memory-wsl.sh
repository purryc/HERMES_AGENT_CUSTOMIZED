#!/usr/bin/env bash
set -euo pipefail

recipients_path="/mnt/f/AGENT/keys/recipients.txt"
encrypted_dir="/mnt/f/AGENT/memory/encrypted"

command -v age >/dev/null 2>&1 || { printf 'age is missing. Run scripts/setup-age-windows.ps1 first.\n' >&2; exit 1; }
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

encrypt_one /mnt/f/AGENT/memory/hermes-raw-memory-export.md "${encrypted_dir}/hermes-raw-memory-export.md.age"
encrypt_one /mnt/f/AGENT/memory/mac-codex-raw-memory-export.md "${encrypted_dir}/mac-codex-raw-memory-export.md.age"

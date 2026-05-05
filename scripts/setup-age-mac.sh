#!/usr/bin/env bash
set -euo pipefail

label="${1:-mac-codex}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/.." && pwd)"
identity_path="${workspace_root}/.secrets/age/${label}.identity.txt"
recipient_path="${workspace_root}/keys/${label}.recipient.txt"
recipients_path="${workspace_root}/keys/recipients.txt"

if ! command -v age >/dev/null 2>&1 || ! command -v age-keygen >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install age
  else
    printf 'age is missing. Install Homebrew, then run: brew install age\n' >&2
    exit 1
  fi
fi

mkdir -p "${workspace_root}/.secrets/age" "${workspace_root}/keys" "${workspace_root}/memory/encrypted"
if [ ! -f "${identity_path}" ]; then
  age-keygen -o "${identity_path}"
fi
chmod 600 "${identity_path}" 2>/dev/null || true

pub="$(grep -E '^# public key: age1' "${identity_path}" | sed 's/^# public key: //')"
if [ -z "${pub}" ]; then
  printf 'Could not find public key in identity file\n' >&2
  exit 1
fi

printf '%s\n' "${pub}" > "${recipient_path}"
touch "${recipients_path}"
grep -qxF "${pub}" "${recipients_path}" || printf '%s\n' "${pub}" >> "${recipients_path}"

printf 'age is ready.\n'
printf 'Private identity: %s\n' "${identity_path}"
printf 'Public recipient: %s\n' "${recipient_path}"
printf 'Recipients list: %s\n' "${recipients_path}"
printf 'Back up the private identity somewhere safe. Do not commit it.\n'

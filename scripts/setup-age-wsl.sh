#!/usr/bin/env bash
set -euo pipefail

label="${1:-windows-hermes-codex}"
identity_path="/mnt/f/AGENT/.secrets/age/${label}.identity.txt"
recipient_path="/mnt/f/AGENT/keys/${label}.recipient.txt"
recipients_path="/mnt/f/AGENT/keys/recipients.txt"

if ! command -v age >/dev/null 2>&1 || ! command -v age-keygen >/dev/null 2>&1; then
  apt-get update
  apt-get install -y age
fi

mkdir -p /mnt/f/AGENT/.secrets/age /mnt/f/AGENT/keys /mnt/f/AGENT/memory/encrypted
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

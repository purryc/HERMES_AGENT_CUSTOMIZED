# Encrypted Raw Memory Sync

Use `age` to encrypt raw memory before committing it to the private GitHub repo.

Plain raw memory stays local and ignored:
- `memory/hermes-raw-memory-export.md`
- `memory/mac-codex-raw-memory-export.md`

Encrypted raw memory can be committed:
- `memory/encrypted/hermes-raw-memory-export.md.age`
- `memory/encrypted/mac-codex-raw-memory-export.md.age`

## Windows / WSL Setup

```powershell
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\setup-age-windows.ps1
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\encrypt-raw-memory.ps1
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\push-memory-github.ps1
```

Decrypt locally:

```powershell
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\decrypt-raw-memory.ps1
```

## Mac Setup

```bash
cd /path/to/hermes-memory
chmod +x scripts/*.sh
./scripts/setup-age-mac.sh
./scripts/encrypt-raw-memory.sh
./scripts/push-memory-github.sh
```

Decrypt locally:

```bash
./scripts/decrypt-raw-memory.sh
```

## Multi-Device Rule

Each machine has its own private identity under `.secrets/age/`.
Each machine commits only its public recipient under `keys/`.
`keys/recipients.txt` should contain every device public recipient that needs to decrypt raw memory.

Never commit `.secrets/age/*.identity.txt`.

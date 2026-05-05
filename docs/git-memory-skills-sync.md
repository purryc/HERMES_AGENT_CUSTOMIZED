# Git Memory And Skills Sync

The private GitHub repo is the simple source of truth for curated shared memory, shared skills, project docs, and setup scripts across three endpoints:

- Windows Hermes Agent
- Windows Codex
- Work Mac Codex

## What Goes In Git

- `memory/SHARED_AGENT_MEMORY.md`
- `memory/mac-codex-memory.md`
- `skills/shared/*`
- `skills/mac-codex/*`
- `AGENTS.md`
- `specs/002-dashboard-companion-chat/plan.md`
- Sync/install scripts
- Setup docs

## What Does Not Go In Git

- Raw Hermes memory export
- Raw Mac Codex memory export
- `auth.json`
- `.env`
- API keys, bot tokens, passwords, private keys
- Encrypted raw memory is intentionally not part of the simple workflow for now.

## Current Shared Skills

- `hermes-blueprint-v3`
- `codex-delegation-workflow`
- `dividend-dashboard-upgrade`

## Windows Workflow

Pull repo updates:

```powershell
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\pull-memory-github.ps1
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\install-shared-skills.ps1
```

Push memory/skill updates:

```powershell
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\push-memory-github.ps1
```

Install daily Windows GitHub sync:

```powershell
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\install-windows-github-memory-sync-task.ps1
```

Default schedule: daily at `23:55`.

What it does:

- Exports Hermes raw memory to the local-only file `memory/hermes-raw-memory-export.md`.
- Pushes only the safe GitHub allowlist through `scripts/push-memory-github.ps1`.
- Keeps raw memory exports, auth files, `.env` files, keys, and tokens out of GitHub.

Run once manually:

```powershell
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\sync-windows-to-github.ps1 -ExportHermesRaw
```

## Mac Workflow

Clone the private repo:

```bash
git clone https://github.com/purryc/hermes-memory.git
cd hermes-memory
chmod +x scripts/*.sh
./scripts/install-mac-codex-memory-sync.sh
./scripts/install-shared-skills.sh
```

Start of day / before work:

```bash
./scripts/sync-mac-from-github.sh
```

End of day / after work:

```bash
./scripts/sync-mac-to-github.sh
```

`sync-mac-to-github.sh` collects Mac Codex memory from `~/.codex/memories` into `memory/mac-codex-memory.md`, copies Mac Codex skills into `skills/mac-codex/<hostname>/`, scans for obvious secrets, and pushes the safe repo state.

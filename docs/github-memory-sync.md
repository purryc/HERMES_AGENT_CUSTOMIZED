# GitHub Memory Sync

GitHub can be used for the curated shared memory bridge, but it should not be used for raw private exports unless the repository is private and you intentionally accept that risk.

Recommended policy:
- Commit `memory/SHARED_AGENT_MEMORY.md`.
- Commit sync scripts and docs.
- Never commit `memory/hermes-raw-memory-export.md`.
- Never commit `memory/mac-codex-raw-memory-export.md`.
- Never commit `~/.codex/auth.json`, `.env`, API keys, bot tokens, or provider secrets.

## Windows Push

After confirming `https://github.com/purryc/hermes-memory` is private:

```powershell
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\push-memory-github.ps1
```

Pull updates:

```powershell
powershell -ExecutionPolicy Bypass -File F:\AGENT\scripts\pull-memory-github.ps1
```

## Mac Push/Pull

From the synced or cloned `AGENT` folder on Mac:

```bash
chmod +x scripts/push-memory-github.sh scripts/pull-memory-github.sh
./scripts/pull-memory-github.sh
./scripts/push-memory-github.sh
```

## Repo Layout

The scripts use a clean mirror at `.memory-git/` so the noisy local `F:\AGENT` workspace is not pushed accidentally. Only an allowlist of safe files is copied into the GitHub repo.

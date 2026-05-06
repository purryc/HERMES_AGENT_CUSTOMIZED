# Mac Memory Sync

Goal: add the work Mac to the same Hermes/Codex shared memory bridge.

## Recommended Sync Layer

Use the private GitHub repo as the simple sync layer for curated memory, original AGENT skills, and project `AGENTS.md` files.

Raw memory exports still stay local-only. The GitHub repo is for curated/safe context, not auth files or raw secret-bearing state.

Do not sync API keys or auth files. The scripts only export memory/context files, not `auth.json`.

## Mac Install

On the Mac, put this repo/folder in the synced location, then run:

```bash
cd /path/to/AGENT
chmod +x scripts/install-mac-codex-memory-sync.sh
./scripts/install-mac-codex-memory-sync.sh
```

This does three things:
- Links `memory/SHARED_AGENT_MEMORY.md` into `~/.codex/memories/shared-agent-memory.md`.
- Exports Mac Codex memory to `memory/mac-codex-raw-memory-export.md`.
- Installs a LaunchAgent that refreshes the export every 30 minutes.

For GitHub sync, use:

```bash
cd /path/to/hermes-memory
./scripts/sync-mac-to-github.sh
```

That command copies original AGENT folder skills into `skills/mac-agent/<hostname>/`.
See `docs/mac-agent-skill-sync.md` for the skill root config.

## Manual Commands

Export once:

```bash
/path/to/AGENT/scripts/export-mac-codex-memory.sh
```

Check the LaunchAgent:

```bash
launchctl print gui/$(id -u)/com.shino.agent-memory-sync
```

Uninstall:

```bash
/path/to/AGENT/scripts/uninstall-mac-codex-memory-sync.sh
```

## Daily Workflow

Mac Codex should read `memory/SHARED_AGENT_MEMORY.md` before substantial work and update it after durable project decisions. The raw export is for recall/debugging; the curated shared memory file is the cross-agent source of truth.

End of day:

```bash
cd /path/to/hermes-memory
./scripts/sync-mac-to-github.sh
```

# Mac Codex Memory Sync

Goal: add the work Mac Codex instance to the same Hermes/Codex shared memory bridge.

## Recommended Sync Layer

Use a private file sync tool to keep the `AGENT/memory` folder available on both machines.

Recommended order:
- Syncthing: best for private local machine-to-machine sync.
- iCloud Drive: easiest on Mac if the Windows side can access the same folder.
- Google Drive/Dropbox/OneDrive: acceptable if you are comfortable storing this private context there.
- Private Git repo: not recommended for raw memory files.

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

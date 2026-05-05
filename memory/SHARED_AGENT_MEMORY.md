# Shared Agent Memory

This file is the shared memory bridge between Hermes Agent and Codex.

Windows path: `F:\AGENT\memory\SHARED_AGENT_MEMORY.md`
WSL path: `/mnt/f/AGENT/memory/SHARED_AGENT_MEMORY.md`

## Ground Rules

- Treat this file as curated memory, not a raw chat log.
- Do not store API keys, bot tokens, passwords, recovery codes, or one-time login codes here.
- Store durable preferences, active projects, architecture decisions, and cross-agent handoff notes.
- If a detail is sensitive but useful, store the minimum useful summary and point to Hermes memory for the full private context.
- When a task changes durable context, update this file after the work is complete.

## User Profile

- Primary language: Chinese.
- Design background, not primarily technical; prefers clear recommendations, concise tradeoff tables, and then practical implementation.
- Uses Windows with WSL Ubuntu-24.04.
- Wants Hermes as the always-on Telegram companion and Codex as the execution layer for code, files, tests, and local automation.

## Active Agent Stack

- Hermes Agent lives in WSL at `/root/.hermes/hermes-agent`.
- Hermes Dashboard runs at `http://127.0.0.1:9119`.
- Hermes Telegram gateway runs in WSL tmux session `hermes`.
- Hermes model provider is OpenRouter.
- Hermes default model is `deepseek/deepseek-v4-flash`.
- Codex CLI is installed in WSL and can be called with `codex exec`.
- WSL Codex root auth is bridged from Windows Codex ChatGPT auth so Hermes can call `codex exec` from terminal tools without hitting OpenAI 401 errors.
- Work Mac Codex can join this memory bridge by running `scripts/install-mac-codex-memory-sync.sh` from a synced copy of this folder.

## Model Routing Policy

- Hermes/OpenRouter handles Telegram intake, everyday chat, reminders, memory, light planning, and coordination.
- Codex handles implementation: repositories, scripts, file edits, tests, desktop/web execution, and batch engineering work.
- For engineering tasks, Hermes should summarize the requested change and then delegate execution to Codex instead of spending OpenRouter budget on implementation.

## Active Projects

- Hermes Agent setup and Dashboard companion work in `F:\AGENT`.
- Dividend Dashboard work is expected under `F:\MyFinanceTool`.
- Knowledge management system uses local Markdown/structured data plus Google Drive/iPad app retrieval.

## Handoff Notes

- Before Codex starts substantial work in `F:\AGENT`, read this file plus `AGENTS.md`.
- Before Hermes delegates to Codex, include relevant user intent, target path, safety constraints, and whether file changes are allowed.
- After Codex completes work that changes long-term context, update this file or tell Hermes what should be saved.
- If Hermes reports `Codex cannot connect to OpenAI API (401 Unauthorized)`, rerun `F:\AGENT\scripts\sync-codex-auth-to-wsl.ps1` and test with `codex exec`.

## Hermes Side: Skills And Tools

Hermes has a skill system at `~/.hermes/skills/`. When delegating to Codex, Hermes loads the relevant skill and injects its content into the Codex prompt.

Key skills for Dividend Dashboard work:
- `dividend-dashboard-upgrade` - Full upgrade plan for data aggregation, Polymarket, spending analysis, and trade scheduling.
- `codex-delegation-workflow` - Hermes to Codex collaboration protocol.
- `hermes-blueprint-v3` - Hermes v3.0 system architecture.

On Hermes side, the shared bridge works like this:
- Hermes reads `SHARED_AGENT_MEMORY.md` when shared project context is needed.
- Hermes writes key updates back to `SHARED_AGENT_MEMORY.md` after sessions when appropriate.
- Hermes built-in memory is auto-exported every 30 minutes via `sync-agent-memory.ps1`.
- Codex should read this file before any substantial work and write back durable handoff notes afterward.

## Hermes Memory Provider Status

- Checked on 2026-05-04: Hermes Agent v0.12.0 has the new memory provider framework.
- Current provider status: built-in only; no external Honcho/Mem0/Hindsight provider is active.
- Built-in memory remains always active at `/root/.hermes/memories/USER.md` and `/root/.hermes/memories/MEMORY.md`.
- The Windows scheduled task `HermesCodexMemorySync` exports those built-in files to `memory/hermes-raw-memory-export.md` every 30 minutes.
- If an external Hermes memory provider is enabled later, update `scripts/sync-agent-memory.ps1` to export that provider too.

## Mac Codex Sync Plan

- Mac Codex should use the same `memory/SHARED_AGENT_MEMORY.md` as the curated cross-agent source of truth.
- The Mac helper script exports `~/.codex/memories` to `memory/mac-codex-raw-memory-export.md`.
- The Mac installer links `memory/SHARED_AGENT_MEMORY.md` into `~/.codex/memories/shared-agent-memory.md` and installs a LaunchAgent that runs every 30 minutes.
- Do not sync Mac `~/.codex/auth.json`; each machine keeps its own login/auth state.

## GitHub Memory Sync Plan

- GitHub repo candidate: `https://github.com/purryc/hermes-memory`.
- Use GitHub only for curated shared memory and sync scripts, not raw memory exports.
- Safe push/pull scripts use `.memory-git/` as a clean mirror and copy only allowlisted files.
- Before first push, confirm the repo is private if personal context should not be public.

## GitHub Skills Sync Plan

- Shared skills live in `skills/shared/` and are safe to sync through the private GitHub repo.
- Current shared skills: `hermes-blueprint-v3`, `codex-delegation-workflow`, `dividend-dashboard-upgrade`.
- Windows installs shared skills with `scripts/install-shared-skills.ps1`.
- Mac installs shared skills with `scripts/install-shared-skills.sh`.
- Hermes receives shared skills under `/root/.hermes/skills/shared`; Codex receives them under `~/.codex/skills`.

## Simple Three-Endpoint GitHub Sync

- The private GitHub repo is the source of truth for curated memory, shared skills, docs, and install scripts.
- The repo intentionally does not sync raw memory exports, auth files, provider secrets, or `.env` files.
- Windows Hermes and Windows Codex install shared skills from `skills/shared/`.
- Work Mac Codex can clone the repo, read `AGENTS.md` and `memory/SHARED_AGENT_MEMORY.md`, then install shared skills with `scripts/install-shared-skills.sh`.
- Work Mac Codex can push its current Codex memory and custom skills with `scripts/sync-mac-to-github.sh`.
- Start-of-day Mac command: `scripts/sync-mac-from-github.sh`.
- End-of-day Mac command: `scripts/sync-mac-to-github.sh`.
- Windows daily GitHub sync uses scheduled task `HermesGitHubMemoryDailySync`, installed by `scripts/install-windows-github-memory-sync-task.ps1`.
- Windows daily GitHub sync exports Hermes raw memory locally, then pushes only the safe allowlist; raw exports, auth files, `.env` files, keys, and tokens stay out of GitHub.

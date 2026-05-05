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
- Prefers low-friction practical setups over over-engineered security workflows; private GitHub sync without encryption is acceptable for now, but secrets must still be excluded.
- Gets frustrated when shell commands block on interactive prompts; prefer non-interactive commands and explain exactly what is happening.
- Wants assistants to be proactive and decisive: inspect the local state, implement the recommended path, verify it, and only ask when a choice has real risk.
- Likes Chinese explanations with concrete commands and clear operational routines.
- Long-term themes include financial independence, family planning, creator/brand work, high design quality, and cross-device workflow across Windows/Mac/iPad.

## User Communication Preferences

- Be concise but not vague; user appreciates a direct diagnosis followed by the command or fix.
- Do not make the user choose inside shell prompts they cannot control. If selection is needed, use a safe default or stop before the interactive step.
- For repeated workflows, create scripts or desktop/task shortcuts instead of asking the user to remember long command chains.
- For sensitive automation, explain what is synced and what is intentionally excluded.
- Avoid pretending sync means "everything"; distinguish curated shared memory, raw local memory, skills, auth, and secrets.

## Active Agent Stack

- Hermes Agent lives in WSL at `/root/.hermes/hermes-agent`.
- Hermes Dashboard runs at `http://127.0.0.1:9119`.
- Hermes Telegram gateway runs in WSL tmux session `hermes`.
- Hermes model provider is OpenRouter.
- Hermes default model is `deepseek/deepseek-v4-flash`.
- Codex CLI is installed in WSL and can be called with `codex exec`.
- WSL Codex root auth is bridged from Windows Codex ChatGPT auth so Hermes can call `codex exec` from terminal tools without hitting OpenAI 401 errors.
- Work Mac Codex can join this memory bridge by running `scripts/install-mac-codex-memory-sync.sh` from a synced copy of this folder.
- Telegram bot integration is the working personal-message gateway after personal WeChat was blocked/unavailable.
- Personal WeChat integration was not viable in the attempted path; Enterprise WeChat was not available to the user.
- Dashboard desktop shortcut exists on Windows and uses an AI-assistant style icon.
- Dashboard update previously failed when Hermes install was not detected as a Git repository; reinstall/update path should account for that.

## Model Routing Policy

- Hermes/OpenRouter handles Telegram intake, everyday chat, reminders, memory, light planning, and coordination.
- Codex handles implementation: repositories, scripts, file edits, tests, desktop/web execution, and batch engineering work.
- For engineering tasks, Hermes should summarize the requested change and then delegate execution to Codex instead of spending OpenRouter budget on implementation.
- ChatGPT/Codex subscription and OpenRouter API billing are separate; do not assume ChatGPT plan credit pays OpenRouter usage.
- Hermes default model target is low-cost OpenRouter routing. Current preferred main model is `deepseek/deepseek-v4-flash`.
- Auxiliary preferred routing: vision/web extraction/compression through Gemini Flash Lite class models, tiny title/search through `gpt-5-nano`, memory reflection through `anthropic/claude-haiku-4.5`, curator through DeepSeek Pro class models.
- Strong models like Claude Sonnet or Grok should be temporary manual switches for high-value tasks, not always-on defaults.

## Active Projects

- Hermes Agent setup and Dashboard companion work in `F:\AGENT`.
- Dividend Dashboard work is expected under `F:\MyFinanceTool`.
- Knowledge management system uses local Markdown/structured data plus Google Drive/iPad app retrieval.
- Dividend Dashboard current target includes stock/dividend analysis, spending analysis, and scheduling/automation support.
- Local shared memory and skill sync repo is `https://github.com/purryc/hermes-memory`; it is private and used as the three-endpoint bridge.

## Important Local Paths

- Windows workspace: `F:\AGENT`
- GitHub sync mirror: `F:\AGENT\.memory-git`
- Shared memory: `F:\AGENT\memory\SHARED_AGENT_MEMORY.md`
- Local-only Hermes raw export: `F:\AGENT\memory\hermes-raw-memory-export.md`
- Windows Codex skills: `C:\Users\User\.codex\skills`
- Hermes shared skills target: `/root/.hermes/skills/shared`
- Hermes built-in memories: `/root/.hermes/memories/USER.md` and `/root/.hermes/memories/MEMORY.md`
- Hermes agent repo: `/root/.hermes/hermes-agent`
- Dashboard URL: `http://127.0.0.1:9119`

## Handoff Notes

- Before Codex starts substantial work in `F:\AGENT`, read this file plus `AGENTS.md`.
- Before Hermes delegates to Codex, include relevant user intent, target path, safety constraints, and whether file changes are allowed.
- After Codex completes work that changes long-term context, update this file or tell Hermes what should be saved.
- If Hermes reports `Codex cannot connect to OpenAI API (401 Unauthorized)`, rerun `F:\AGENT\scripts\sync-codex-auth-to-wsl.ps1` and test with `codex exec`.
- If Hermes says Codex is unavailable with OpenAI 401, prefer fixing auth bridge instead of letting OpenRouter model do a large coding job directly.
- If Hermes blocks on project startup, inspect whether it is in WSL vs Windows path and whether dependencies were installed in the right environment.
- If the task involves GitHub memory sync, use the `.memory-git` mirror and the allowlist scripts, not the noisy `F:\AGENT` worktree.

## Operating Routines

- Windows manual safe sync to GitHub: `powershell -NoProfile -ExecutionPolicy Bypass -File F:\AGENT\scripts\sync-windows-to-github.ps1 -ExportHermesRaw`
- Windows pull from GitHub: `powershell -NoProfile -ExecutionPolicy Bypass -File F:\AGENT\scripts\pull-memory-github.ps1`
- Windows install shared skills: `powershell -NoProfile -ExecutionPolicy Bypass -File F:\AGENT\scripts\install-shared-skills.ps1`
- Mac start-of-day sync: `./scripts/sync-mac-from-github.sh`
- Mac end-of-day sync: `./scripts/sync-mac-to-github.sh`
- Mac first clone: `git clone https://github.com/purryc/hermes-memory.git && cd hermes-memory && chmod +x scripts/*.sh`
- Daily Windows GitHub sync task: `HermesGitHubMemoryDailySync`, scheduled at 23:55 local time.
- Local Hermes raw memory export task: `HermesCodexMemorySync`, every 30 minutes.

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
- Checked on 2026-05-05: shared memory was too sparse; expanded this file with durable operational context so GitHub sync is more useful.

## Memory Sync Boundaries

- `memory/SHARED_AGENT_MEMORY.md` is the curated memory that should go to GitHub and be read by Codex/Hermes/Mac Codex.
- `memory/hermes-raw-memory-export.md` is local-only and can contain sensitive private context.
- `memory/mac-codex-memory.md` is the Mac-side curated/sanitized export target that may go to GitHub.
- `skills/shared/*` are cross-agent skills that should go to GitHub.
- `skills/mac-codex/*` stores Mac Codex custom skill snapshots after Mac runs its end-of-day sync.
- Never sync `auth.json`, `.env`, provider configs with keys, bot tokens, private keys, recovery codes, or one-time login codes.
- If user asks for "all memory", clarify whether they mean curated shared memory, raw local export, or searchable long-term memory provider.

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

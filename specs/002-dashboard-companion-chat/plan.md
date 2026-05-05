# Implementation Plan: Dashboard Companion Chat

**Branch**: `002-dashboard-companion-chat` | **Date**: 2026-04-30 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/002-dashboard-companion-chat/spec.md`

## Summary

Add a dashboard-native companion chat path for M5S3 sessions. The local Windows
agent remains the source of truth for companion message handling and persistence,
while the WSL Hermes dashboard exposes a narrow proxy and UI composer for the
synthetic M5S3 session. Text sending is the MVP; multimedia v1 validates and
persists attachment metadata so the history can show rich desktop context.

## Technical Context

**Language/Version**: Python 3.11, TypeScript/React 19, Vite  
**Primary Dependencies**: Existing `http.server`-based local agent, FastAPI-based Hermes dashboard, React dashboard UI  
**Storage**: Existing local SQLite `data/state.db` records store; dashboard reads through WSL path `/mnt/f/AGENT/data/state.db`  
**Testing**: Python `unittest` for local agent routes; TypeScript build for dashboard UI  
**Target Platform**: Windows local agent, WSL-hosted dashboard at `127.0.0.1:9119`, browser dashboard  
**Project Type**: Local web dashboard plus local HTTP service  
**Performance Goals**: Dashboard text send returns a visible result within 10 seconds in normal local operation  
**Constraints**: Preserve Telegram/TUI dashboard behavior; M5S3 synthetic sessions must not be treated as native TUI sessions; no physical device required for tests  
**Scale/Scope**: One companion session MVP (`m5stick-s3-pet-01` / `main-session`) with text and attachment metadata

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- User-Visible Companion Loop: PASS. Each send has success or failure state in dashboard history.
- Local-First Control Surface: PASS. The local agent owns handling and persistence.
- Testable Routing and Persistence: PASS. Tests cover route handling and persisted messages.
- Safe Desktop and Browser Actions: PASS. This feature does not perform desktop actions directly.
- Small, Reversible Integrations: PASS. Dashboard changes are additive proxy/UI behavior.

## Project Structure

### Documentation (this feature)

```text
specs/002-dashboard-companion-chat/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- companion-dashboard-chat.md
|-- checklists/
|   `-- requirements.md
`-- tasks.md
```

### Source Code (repository root)

```text
hermes_personal_agent/
|-- server.py
|-- voice_turns.py
`-- schemas.py

tests/
`-- test_agent.py

/root/.hermes/hermes-agent/
|-- hermes_cli/web_server.py
|-- venv/lib/python3.11/site-packages/hermes_cli/web_server.py
`-- web/src/pages/SessionsPage.tsx
```

**Structure Decision**: Implement local companion handling in the repository
agent code and keep dashboard proxy/UI changes narrow in the installed Hermes
dashboard patch locations already used for M5S3 visibility.

## Complexity Tracking

No constitution violations.

# Tasks: Dashboard Companion Chat

**Input**: Design documents from `specs/002-dashboard-companion-chat/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Include regression tests for local agent routing/persistence and run
dashboard TypeScript build for UI validation.

## Phase 1: Setup

**Purpose**: Confirm current runtime boundaries and document scope.

- [x] T001 Verify local agent and dashboard ports in `specs/002-dashboard-companion-chat/quickstart.md`

---

## Phase 2: Foundational

**Purpose**: Add local companion text-turn capability before dashboard UI sends messages.

- [x] T002 [P] Add local agent test for dashboard text turns in `tests/test_agent.py`
- [x] T003 Implement dashboard text turn creation in `hermes_personal_agent/voice_turns.py`
- [x] T004 Expose `POST /api/companion/text-turns` in `hermes_personal_agent/server.py`

---

## Phase 3: User Story 1 - Send Text To M5S3 Session (Priority: P1) MVP

**Goal**: User sends text from dashboard and sees the reply in M5S3 history.

**Independent Test**: POST a text turn locally, then read M5S3 messages through dashboard history.

- [x] T005 [US1] Add WSL dashboard proxy endpoint in `/root/.hermes/hermes-agent/hermes_cli/web_server.py`
- [x] T006 [US1] Mirror dashboard proxy patch in `/root/.hermes/hermes-agent/venv/lib/python3.11/site-packages/hermes_cli/web_server.py`
- [x] T007 [US1] Add companion composer UI to `/root/.hermes/hermes-agent/web/src/pages/SessionsPage.tsx`
- [x] T008 [US1] Build and sync dashboard web assets from `/root/.hermes/hermes-agent/web`
- [x] T009 [US1] Run local text-turn regression test and verify dashboard messages API

---

## Phase 4: User Story 2 - Attach Multimedia Metadata (Priority: P2)

**Goal**: User can send a message with validated attachment metadata.

**Independent Test**: Send allowed attachment metadata and verify it appears in history; reject invalid input.

- [x] T010 [P] [US2] Add attachment validation tests in `tests/test_agent.py`
- [x] T011 [US2] Validate and persist attachment metadata in `hermes_personal_agent/voice_turns.py`
- [x] T012 [US2] Display attachment metadata in `/root/.hermes/hermes-agent/web/src/pages/SessionsPage.tsx`

---

## Phase 5: User Story 3 - Prevent Wrong TUI Resume (Priority: P3)

**Goal**: M5S3 sessions never open the ended TUI terminal.

**Independent Test**: Open `/chat?resume=m5s3:main-session` and verify redirect to expanded sessions.

- [x] T013 [US3] Redirect M5S3 resume URLs in `/root/.hermes/hermes-agent/web/src/pages/ChatPage.tsx`
- [x] T014 [US3] Hide TUI resume and delete controls for M5S3 rows in `/root/.hermes/hermes-agent/web/src/pages/SessionsPage.tsx`

---

## Phase 6: Polish & Validation

- [x] T015 Run `py -m unittest F:\AGENT\tests\test_agent.py -k companion`
- [x] T016 Run dashboard `npm run build` in `/root/.hermes/hermes-agent/web`
- [x] T017 Restart local agent and dashboard, then validate quickstart manually
- [x] T018 Render default `/chat` as a dashboard-native companion chat in `/root/.hermes/hermes-agent/web/src/pages/ChatPage.tsx`

## Dependencies & Execution Order

- T002 before T003-T004.
- T003-T004 before dashboard proxy/UI tasks.
- T005-T008 before T009.
- T010 before T011-T012.
- T013-T014 already completed as an emergency UX correction.

## Implementation Strategy

Deliver MVP text send first (US1), then attachment metadata (US2). Keep all
dashboard patches additive and preserve Telegram/TUI behavior.

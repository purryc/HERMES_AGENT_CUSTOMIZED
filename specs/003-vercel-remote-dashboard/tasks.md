# Tasks: Vercel Remote Dashboard MVP

**Input**: Design documents from `specs/003-vercel-remote-dashboard/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Run Python guard tests and `npm run build` in `remote-dashboard`.

## Phase 1: Setup

**Purpose**: Isolate the Vercel app and document the remote access boundary.

- [x] T001 Create Spec Kit artifacts for `003-vercel-remote-dashboard`
- [x] T002 Update `AGENTS.md` current plan pointer to `specs/003-vercel-remote-dashboard/plan.md`

---

## Phase 2: Foundational

**Purpose**: Add protected local tunnel infrastructure before remote UI calls it.

- [x] T003 [P] Implement local guarded proxy in `scripts/hermes_tunnel_guard.py`
- [x] T004 [P] Add guard tests in `tests/test_tunnel_guard.py`
- [x] T005 Add PowerShell tunnel start script in `scripts/start-hermes-cloudflare-tunnel.ps1`
- [x] T006 Add PowerShell tunnel stop script in `scripts/stop-hermes-cloudflare-tunnel.ps1`

---

## Phase 3: User Story 1 - Remote Companion Chat (Priority: P1) MVP

**Goal**: Vercel page can health-check local Hermes and send companion text through the protected path.

**Independent Test**: Build the app and call the proxy with correct/missing token in local or deployed mode.

- [x] T007 [US1] Create `remote-dashboard/package.json`, TypeScript, Vite, and env examples
- [x] T008 [US1] Implement Vercel proxy in `remote-dashboard/api/hermes/[...path].ts`
- [x] T009 [US1] Implement remote UI in `remote-dashboard/src/App.tsx`
- [x] T010 [US1] Add UI styling in `remote-dashboard/src/styles.css`

---

## Phase 4: User Story 2 - Safe Tunnel Startup (Priority: P2)

**Goal**: One PowerShell command starts the guarded proxy and Cloudflare tunnel and writes local state.

**Independent Test**: Run the start script and verify it prints a trycloudflare URL; run stop script and verify processes stop.

- [x] T011 [US2] Validate local Hermes `/healthz` before tunnel startup
- [x] T012 [US2] Persist ignored tunnel state under `data/hermes-remote-tunnel.json`
- [x] T013 [US2] Document generated token handling and Vercel env mapping

---

## Phase 5: User Story 3 - Deployment Instructions (Priority: P3)

**Goal**: User can deploy the remote dashboard to Vercel and verify it.

**Independent Test**: Follow docs and confirm Vercel build settings/env vars are clear.

- [x] T014 [US3] Add deployment guide in `docs/vercel-remote-dashboard.md`
- [x] T015 [US3] Add README link to the remote dashboard guide

---

## Phase 6: Validation

- [x] T016 Run `py -m unittest F:\AGENT\tests\test_tunnel_guard.py`
- [x] T017 Run `npm install` and `npm run build` in `F:\AGENT\remote-dashboard`
- [x] T018 Run local guard smoke test against `http://127.0.0.1:8787/healthz` when Hermes is running

## Dependencies & Execution Order

- T003-T006 before Cloudflare tunnel validation.
- T007-T010 before Vercel deploy validation.
- T014-T015 after implementation paths are stable.
- T016-T018 last.

## Implementation Strategy

Deliver P1 first: protected proxy + health/chat UI. Then make startup easier with
scripts and document the exact Vercel setup.

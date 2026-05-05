# Feature Specification: Vercel Remote Dashboard MVP

**Feature Branch**: `003-vercel-remote-dashboard`  
**Created**: 2026-05-05  
**Status**: Draft  
**Input**: User wants the fastest usable remote access path: Vercel frontend plus Cloudflare Tunnel back to the local Hermes Agent.

## User Scenarios & Testing

### User Story 1 - Remote Companion Chat (Priority: P1)

The user opens a Vercel-hosted page from another device, enters a remote access token, checks local Hermes health, and sends a text message to the M5S3 companion session through the local Hermes Agent.

**Why this priority**: This proves the whole remote path end-to-end without moving Hermes/Codex execution off the local machine.

**Independent Test**: Start local Hermes, start the guarded Cloudflare tunnel, run the remote dashboard locally with the same env vars, and send a companion text turn that returns `status=done`.

**Acceptance Scenarios**:

1. **Given** local Hermes is reachable and the tunnel is configured, **When** the user enters the correct token and sends text, **Then** the page shows the turn status, intent, and reply text.
2. **Given** the user enters no token or a wrong token, **When** they call the proxy, **Then** the request is rejected before reaching local Hermes.

---

### User Story 2 - Safe Tunnel Startup (Priority: P2)

The user can run one PowerShell script that starts a local guarded proxy and a Cloudflare quick tunnel, then prints the tunnel URL and token values needed for Vercel.

**Why this priority**: The user prefers low-friction scripts and should not have to remember multi-command tunnel setup.

**Independent Test**: Run the script with Hermes listening on `127.0.0.1:8787`; verify it writes a local tunnel state file and reports a `https://*.trycloudflare.com` URL.

**Acceptance Scenarios**:

1. **Given** `cloudflared` is installed, **When** the script runs, **Then** it starts a guarded local proxy and Cloudflare tunnel.
2. **Given** local Hermes is not healthy, **When** the script runs, **Then** it fails with a clear message instead of exposing an unusable tunnel.

---

### User Story 3 - Deployment Instructions (Priority: P3)

The user can deploy the remote dashboard to Vercel with clear environment variables and a quick verification checklist.

**Why this priority**: Vercel auth may require a browser login, so the implementation should give deterministic commands and a manual fallback.

**Independent Test**: Follow the quickstart and verify Vercel has `HERMES_TUNNEL_URL` and `REMOTE_DASHBOARD_TOKEN`, then open the deployed URL and pass the health check.

**Acceptance Scenarios**:

1. **Given** the user has a Vercel account, **When** they follow the documented setup, **Then** the remote dashboard deploys from `remote-dashboard`.
2. **Given** the tunnel URL changes, **When** the user updates the Vercel env var and redeploys, **Then** the page points to the new local Hermes tunnel.

## Edge Cases

- Cloudflare quick tunnel URL changes after restart; the user must update `HERMES_TUNNEL_URL` in Vercel.
- The Vercel proxy must fail closed if `REMOTE_DASHBOARD_TOKEN` or `HERMES_TUNNEL_URL` is missing.
- The local tunnel guard must reject requests without the shared token.
- The remote dashboard must display connection errors clearly instead of pretending Hermes accepted a command.
- The MVP does not expose arbitrary local file, Codex terminal, or browser-control APIs.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a deployable Vercel subproject under `remote-dashboard`.
- **FR-002**: System MUST include a Vercel serverless proxy endpoint that forwards only approved Hermes API paths to `HERMES_TUNNEL_URL`.
- **FR-003**: System MUST require `REMOTE_DASHBOARD_TOKEN` on the browser-to-Vercel request.
- **FR-004**: System MUST forward the same remote token to the local tunnel guard so the public Cloudflare URL is not enough to access Hermes.
- **FR-005**: System MUST include a local tunnel guard that proxies only approved paths to `http://127.0.0.1:8787`.
- **FR-006**: System MUST include a PowerShell script to start the tunnel guard and Cloudflare quick tunnel.
- **FR-007**: System MUST provide a remote UI for health check and `POST /api/companion/text-turns`.
- **FR-008**: System MUST document Vercel env vars, tunnel startup, deployment, verification, and shutdown.
- **FR-009**: System MUST not commit `.env`, tunnel state, tokens, local databases, or Cloudflare logs.

### Key Entities

- **Remote Dashboard Token**: Shared secret entered by the user in the Vercel UI and configured as `REMOTE_DASHBOARD_TOKEN` on Vercel.
- **Tunnel URL**: The Cloudflare quick tunnel URL configured as `HERMES_TUNNEL_URL` on Vercel.
- **Companion Text Turn**: Existing Hermes local API request with `device_id`, `session_id`, `text`, and optional attachment metadata.
- **Tunnel State**: Local ignored file containing process IDs, tunnel URL, and token for operational convenience.

## Success Criteria

### Measurable Outcomes

- **SC-001**: User can start the local tunnel from one PowerShell command.
- **SC-002**: User can build the Vercel subproject with `npm run build`.
- **SC-003**: Wrong or missing token returns `401` from the Vercel proxy or local tunnel guard.
- **SC-004**: Correct token can reach `/healthz` and send one companion text turn through the tunnel path.

## Assumptions

- Local Hermes Agent continues running on `127.0.0.1:8787`.
- Cloudflare quick tunnels are acceptable for this MVP; stable named tunnels can be added later.
- Vercel deploy/login may require user browser interaction, so Codex will create deployable assets and scripts rather than assuming Vercel CLI is already authenticated.
- Remote dashboard v1 is text-first and intentionally excludes full TUI/WebSocket terminal control.

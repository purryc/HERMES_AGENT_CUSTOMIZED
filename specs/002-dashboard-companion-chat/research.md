# Research: Dashboard Companion Chat

## Decision: Local agent owns companion text turns

**Rationale**: The local agent already owns companion session persistence,
conversation memory, routing, and reply generation. Keeping that ownership
prevents the dashboard from becoming a second brain with divergent history.

**Alternatives considered**:
- Generate replies directly inside the WSL dashboard. Rejected because it would
  duplicate routing and model behavior.
- Write dashboard messages directly into `state.db` without reply generation.
  Rejected because users need a real conversation, not a log-only surface.

## Decision: Dashboard uses a narrow proxy for M5S3 send

**Rationale**: The dashboard runs in WSL while the local agent runs on Windows.
A proxy endpoint can hide runtime-boundary details from the React UI and keep
browser calls same-origin with the dashboard session token.

**Alternatives considered**:
- Browser calls the Windows local agent directly. Rejected due CORS, host
  discovery, and security friction.
- Use only the Cloudflare tunnel URL from the browser. Rejected because local
  dashboard behavior should not depend on public tunnel availability.

## Decision: Multimedia v1 stores attachment metadata

**Rationale**: The user wants multimedia messages, but deep media processing
requires additional model and storage decisions. Metadata-first support lets the
dashboard show what was sent and keeps the message model extensible.

**Alternatives considered**:
- Full multimodal analysis immediately. Rejected as too broad for the first
  safe increment.
- Ignore multimedia until later. Rejected because the UI and data contract
  should not paint us into a text-only corner.

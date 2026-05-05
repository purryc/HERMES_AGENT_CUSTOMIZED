# Research: Vercel Remote Dashboard MVP

## Decision: Vercel hosts a thin UI plus serverless HTTP proxy

- **Rationale**: The remote dashboard needs normal HTTP calls for health checks
  and companion text turns. It does not need to host Hermes, Codex, or long-lived
  PTY/WebSocket terminal sessions.
- **Alternative rejected**: Deploying the existing Hermes dashboard directly to
  Vercel. The installed dashboard depends on local FastAPI, PTY, WebSockets, and
  local runtime state that belong on the user's machine.

## Decision: Cloudflare quick tunnel points to a local guard, not directly to Hermes

- **Rationale**: The quick tunnel URL is public. The existing local Hermes API
  does not have a remote access auth layer, so a lightweight local guard reduces
  accidental exposure while keeping the MVP fast.
- **Alternative rejected**: Tunnel directly to `127.0.0.1:8787`. That works but
  makes URL leakage enough to call local Hermes endpoints.

## Decision: Shared remote token for browser, Vercel proxy, and local guard

- **Rationale**: One token keeps the first setup simple. Browser requests must
  present the token to Vercel; Vercel forwards it to the local guard. The token
  lives in Vercel env and local ignored state, not in Git.
- **Future improvement**: Split into `REMOTE_DASHBOARD_TOKEN` and
  `HERMES_TUNNEL_SECRET`, add token rotation and per-device access.

## Decision: Allowlisted Hermes paths only

- **Rationale**: The remote MVP should prove useful companion chat without
  exposing arbitrary local APIs. Allowlisting protects against accidental broad
  remote control.
- **Allowed MVP paths**: `/healthz`, `/api/companion/text-turns`,
  `/api/companion/voice-turns`, `/api/companion/audio`, `/api/jobs`, and
  `/api/skills`.

## Decision: Root Directory `remote-dashboard` on Vercel

- **Rationale**: This repo includes firmware, scripts, Python code, and Spec Kit
  assets. A subproject keeps Vercel install/build focused and fast.
- **Build command**: `npm run build`
- **Output directory**: `dist`

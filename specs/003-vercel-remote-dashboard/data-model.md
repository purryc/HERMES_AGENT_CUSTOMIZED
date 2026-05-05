# Data Model: Vercel Remote Dashboard MVP

## RemoteDashboardConfig

- `HERMES_TUNNEL_URL`: HTTPS URL for the current Cloudflare quick tunnel.
- `REMOTE_DASHBOARD_TOKEN`: Shared access token required by Vercel proxy and local guard.
- `DEFAULT_DEVICE_ID`: Optional UI default; fallback `m5stick-s3-pet-01`.
- `DEFAULT_SESSION_ID`: Optional UI default; fallback `main-session`.

## TunnelState

Local ignored JSON written under `data/hermes-remote-tunnel.json`.

- `guard_pid`: Process ID for local Python tunnel guard.
- `cloudflared_pid`: Process ID for Cloudflare quick tunnel.
- `local_guard_url`: Local URL exposed to cloudflared, default `http://127.0.0.1:8790`.
- `target_url`: Local Hermes target, default `http://127.0.0.1:8787`.
- `tunnel_url`: Public Cloudflare tunnel URL.
- `token_path`: Local ignored token file path.
- `started_at`: ISO timestamp.

## ProxyRequest

- `path`: Hermes API path supplied as the `/api/hermes?path=` query parameter.
- `method`: HTTP method.
- `token`: Browser-supplied `X-Remote-Dashboard-Token` or bearer token.
- `body`: JSON payload for companion text turns or job operations.

## CompanionTextTurnRequest

Existing local Hermes payload:

- `device_id`: Device identifier.
- `session_id`: Companion session identifier.
- `text`: Message text.
- `attachments`: Optional metadata list; remote MVP defaults to empty.

## ProxyResponse

- `status`: HTTP status from guard/Hermes or proxy auth failure.
- `content_type`: Preserved response content type where possible.
- `body`: JSON for Hermes API responses or error object from proxy/guard.

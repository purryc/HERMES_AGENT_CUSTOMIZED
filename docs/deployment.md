# Deployment Guide

## Recommended Topology

### Milestone 1

- Run this starter API on a VPS or always-on home machine.
- Route model calls through OpenRouter.
- Use the current local control plane as the message and approval boundary.

### Milestone 2

- Expose a real WeCom callback URL.
- Add alerting and operator notifications for failures.

### Milestone 3

- Add low-risk tool execution.
- Add visual inputs and audit logs.

### Milestone 4

- Connect the companion client.
- Support offline queueing and retry delivery.

## Local Run

```powershell
py -m hermes_personal_agent.cli serve --config F:\AGENT\config\agent.example.json --host 127.0.0.1 --port 8787
```

## WeCom Callback Setup

1. In the WeCom self-built app settings, enable message reception.
2. Set the callback URL to `https://your-domain.example/api/wecom/callback`
3. Set the same values in the local environment:

```powershell
$env:WECOM_TOKEN="your-token"
$env:WECOM_ENCODING_AES_KEY="your-43-char-encoding-aes-key"
$env:WECOM_CORP_ID="wwxxxxxxxxxxxxxxxx"
$env:WECOM_AGENT_ID="1000002"
```

4. This service now supports:
   - `GET /api/wecom/callback` for URL verification
   - `POST /api/wecom/callback` for encrypted callback delivery

Current behavior:

- text messages route into the existing workflow engine
- voice messages use `Recognition` text when WeCom provides it
- menu click events route `EventKey` into the same workflow engine
- low-signal events are acknowledged with `200` and ignored

## Docker Run

```powershell
docker compose -f F:\AGENT\docker-compose.example.yml up --build
```

## Production Notes

- Put the callback URL behind a reverse proxy like Nginx or Caddy.
- Keep `OPENROUTER_API_KEY` and WeCom secrets in environment variables or a secret manager.
- Persist the `data/` directory.
- Prefer webhook or WeCom callback ingress over brittle personal-account automation.
- Keep high-risk actions behind explicit approval.

## Real Hermes Integration Path

1. Use Hermes for long-term memory, tools, dashboard, and broader agent runtime.
2. Keep this project focused on message ingress, approvals, and device-side boundaries.
3. Gradually replace simplified local logic with real Hermes session, memory, and tool integrations.

# Vercel Remote Dashboard MVP

This is the fastest safe-ish remote access path:

```text
Remote browser
  -> Vercel remote-dashboard UI
  -> Vercel /api/hermes?path=... proxy
  -> Cloudflare quick tunnel
  -> local Hermes tunnel guard on 127.0.0.1:8790
  -> local Hermes Agent on 127.0.0.1:8787
```

The quick tunnel does **not** point directly at Hermes. It points at a local guard
that requires `X-Hermes-Remote-Token` and only forwards an allowlist of Hermes
paths.

## Start Local Hermes

```powershell
py -3.10 -m hermes_personal_agent.cli serve --config F:\AGENT\config\agent.example.json --host 127.0.0.1 --port 8787
```

## Start Tunnel

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File F:\AGENT\scripts\start-hermes-cloudflare-tunnel.ps1
```

The script prints:

```text
HERMES_TUNNEL_URL=https://something.trycloudflare.com
REMOTE_DASHBOARD_TOKEN=...
```

Keep the token private. It is stored locally under `F:\AGENT\data\`, which is
ignored by Git.

## Deploy to Vercel

Use this GitHub repo and set Vercel's root directory to:

```text
remote-dashboard
```

Build settings:

```text
Install command: npm install
Build command: npm run build
Output directory: dist
```

Environment variables:

```text
HERMES_TUNNEL_URL=<printed trycloudflare URL>
REMOTE_DASHBOARD_TOKEN=<printed token>
```

If using Vercel CLI:

```powershell
cd F:\AGENT\remote-dashboard
npm install
npx vercel login
npx vercel --yes --prod --env "HERMES_TUNNEL_URL=<printed trycloudflare URL>" --env "REMOTE_DASHBOARD_TOKEN=<printed token>"
```

Vercel env var entry is usually interactive. The command above avoids that by
injecting the two runtime variables into the production deployment.

## Use It

### One-click local launcher

Use the desktop shortcut:

```text
Hermes Remote Dashboard
```

It starts the local Hermes Dashboard, starts a protected Cloudflare tunnel,
updates the Vercel production deployment with the current tunnel URL, copies the
remote token to the clipboard, and opens the Vercel URL.

After the page opens:

1. Paste the copied token into `REMOTE TOKEN`.
2. Click `CHECK HEALTH`.
3. Send a message to the M5S3 companion.

### Manual use

1. Open the Vercel URL.
2. Paste `REMOTE_DASHBOARD_TOKEN`.
3. Click `Check Health`.
4. Send a message to the M5S3 companion.

## Stop Tunnel

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File F:\AGENT\scripts\stop-hermes-cloudflare-tunnel.ps1
```

## Current MVP Limits

- Text companion messages only.
- No remote Codex terminal/TUI WebSocket.
- No arbitrary local file or browser-control API exposure.
- Cloudflare quick tunnel URL changes when restarted; update Vercel
  `HERMES_TUNNEL_URL` and redeploy.

## Troubleshooting

- `remote_dashboard_not_configured`: Vercel is missing `HERMES_TUNNEL_URL` or
  `REMOTE_DASHBOARD_TOKEN`.
- `unauthorized`: Token entered in the browser does not match Vercel env.
- `upstream_unreachable`: Tunnel is down, local guard is down, or local Hermes is
  not listening on `127.0.0.1:8787`.
- `path_not_allowed`: The proxy blocked a route outside the MVP allowlist.

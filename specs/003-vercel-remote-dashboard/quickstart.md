# Quickstart: Vercel Remote Dashboard MVP

## 1. Start local Hermes

```powershell
py -3.10 -m hermes_personal_agent.cli serve --config F:\AGENT\config\agent.example.json --host 127.0.0.1 --port 8787
```

## 2. Start guarded Cloudflare tunnel

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File F:\AGENT\scripts\start-hermes-cloudflare-tunnel.ps1
```

The script prints:

- `HERMES_TUNNEL_URL`
- `REMOTE_DASHBOARD_TOKEN`

## 3. Configure Vercel

Deploy with Vercel root directory:

```text
remote-dashboard
```

Required Vercel environment variables:

```text
HERMES_TUNNEL_URL=<printed trycloudflare URL>
REMOTE_DASHBOARD_TOKEN=<printed token>
```

Build command:

```text
npm run build
```

Output directory:

```text
dist
```

## 4. Verify locally before deploy

```powershell
cd F:\AGENT\remote-dashboard
npm install
npm run build
```

## 5. Open Vercel URL

Enter the same token shown by the tunnel script, click health check, then send a
message to the M5S3 companion.

## 6. Stop tunnel

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File F:\AGENT\scripts\stop-hermes-cloudflare-tunnel.ps1
```

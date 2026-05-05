# Contract: Remote Dashboard Proxy

## Browser to Vercel

All remote Hermes calls go through:

```text
/api/hermes?path=<url-encoded-hermes-path>
```

Required header:

```text
X-Remote-Dashboard-Token: <REMOTE_DASHBOARD_TOKEN>
```

Bearer auth is also accepted:

```text
Authorization: Bearer <REMOTE_DASHBOARD_TOKEN>
```

### GET `/api/hermes?path=%2Fhealthz`

Returns local Hermes health response.

Expected success:

```json
{ "ok": true }
```

### POST `/api/hermes?path=%2Fapi%2Fcompanion%2Ftext-turns`

Request:

```json
{
  "device_id": "m5stick-s3-pet-01",
  "session_id": "main-session",
  "text": "hello from remote dashboard",
  "attachments": []
}
```

Expected success includes existing Hermes serialized turn fields:

```json
{
  "status": "done",
  "intent": "companion_chat",
  "reply_text": "...",
  "turn_id": "turn_..."
}
```

### Error Responses

Missing or wrong token:

```json
{ "error": "unauthorized" }
```

Missing Vercel env:

```json
{ "error": "remote_dashboard_not_configured" }
```

Blocked path:

```json
{ "error": "path_not_allowed" }
```

## Vercel to Local Tunnel Guard

The Vercel proxy forwards to:

```text
<HERMES_TUNNEL_URL>/<hermes-path>
```

Required forwarded header:

```text
X-Hermes-Remote-Token: <REMOTE_DASHBOARD_TOKEN>
```

The local guard rejects any request missing this header or targeting a path not
listed in the allowlist.

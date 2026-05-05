# Contract: Companion Dashboard Chat

## Local Agent Endpoint

### `POST /api/companion/text-turns`

Creates a companion turn from dashboard-entered text and optional attachment
metadata.

Request JSON:

```json
{
  "device_id": "m5stick-s3-pet-01",
  "session_id": "main-session",
  "text": "你好，帮我继续刚才的话题",
  "attachments": [
    {
      "filename": "photo.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 12345
    }
  ]
}
```

Success response:

```json
{
  "id": "turn_...",
  "device_id": "m5stick-s3-pet-01",
  "session_id": "main-session",
  "status": "done",
  "transcript": "你好，帮我继续刚才的话题",
  "reply_text": "当然，我们继续。",
  "attachments": []
}
```

Failure response:

```json
{
  "error": "text_or_attachment_required"
}
```

## Dashboard Proxy Endpoint

### `POST /api/m5/companion-chat`

Same-origin dashboard endpoint that forwards validated requests to the local
agent and returns the local agent response. Requires the dashboard session token
like other protected dashboard APIs.

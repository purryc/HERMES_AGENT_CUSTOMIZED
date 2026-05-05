# Data Model: Dashboard Companion Chat

## Companion Dashboard Message

Represents a dashboard-originated message sent into an M5S3 companion session.

Fields:
- `id`: unique turn/message identifier
- `device_id`: companion device id
- `session_id`: companion session id
- `conversation_id`: linked companion conversation id
- `source`: `dashboard`
- `status`: `done` or `error`
- `transcript`: user-entered text
- `reply_text`: assistant reply text
- `display_text`: dashboard-visible reply text
- `created_at`: message creation timestamp
- `updated_at`: last status update timestamp
- `attachments`: list of attachment metadata
- `event_log`: lifecycle events

Validation:
- Text must be non-empty unless at least one valid attachment is present.
- Session id defaults to `main-session` for the M5S3 MVP.
- Device id defaults to `m5stick-s3-pet-01` for the M5S3 MVP.

## Companion Attachment

Represents a multimedia item associated with a dashboard message.

Fields:
- `id`: attachment identifier
- `filename`: sanitized display filename
- `content_type`: declared content type
- `size_bytes`: uploaded size
- `status`: `accepted` or `rejected`
- `storage_ref`: optional local storage reference for future retrieval

Validation:
- Filename must be sanitized before display.
- Size must be under the configured limit.
- Content type must be allowed by the companion dashboard policy.

## Companion Session

Existing session record in local agent state.

Relationships:
- Has many companion dashboard messages and voice turns.
- Maintains `recent_turns` for quick dashboard display.
- Links to a conversation record for longer chat history.

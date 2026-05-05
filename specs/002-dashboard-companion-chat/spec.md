# Feature Specification: Dashboard Companion Chat

**Feature Branch**: `002-dashboard-companion-chat`  
**Created**: 2026-04-30  
**Status**: Draft  
**Input**: User description: "Dashboard 为什么不能用对话页面直接对话，我希望这个也能直接发消息，多媒体消息"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send Text To M5S3 Session (Priority: P1)

As the device owner, I want to type into the dashboard companion session and get
a reply in the same M5S3 conversation history, so I can continue the companion
conversation from my computer without speaking into the device.

**Why this priority**: This removes the main confusion: the dashboard should be
a real companion chat surface, not only a read-only history or TUI resume link.

**Independent Test**: Open the M5S3 session from the dashboard, send a text
message, and verify both the user message and assistant reply appear in the
expanded history.

**Acceptance Scenarios**:

1. **Given** the M5S3 session exists in dashboard history, **When** the owner
   sends a text message from the dashboard, **Then** the message is appended to
   that session and an assistant reply appears in the same history.
2. **Given** the local companion runtime is unavailable, **When** the owner sends
   a text message, **Then** the dashboard shows a clear failure and does not
   silently create a fake successful reply.

---

### User Story 2 - Attach Multimedia To Companion Session (Priority: P2)

As the device owner, I want to attach an image, audio file, or other media from
the dashboard, so the companion history records richer context even when the
device itself only supports voice.

**Why this priority**: Multimedia makes the dashboard useful as the richer
desktop control surface while preserving the small-device experience.

**Independent Test**: Attach a media file to the M5S3 session and verify the
history shows the attachment metadata alongside the message.

**Acceptance Scenarios**:

1. **Given** the owner selects a supported attachment, **When** the dashboard
   sends the message, **Then** the session history shows the attachment name,
   type, and size with the message.
2. **Given** an attachment is too large or unsupported, **When** the owner tries
   to send it, **Then** the dashboard rejects it with a visible explanation.

---

### User Story 3 - Prevent Wrong TUI Resume For Companion Sessions (Priority: P3)

As the device owner, I want M5S3 session controls to open the correct companion
chat view, so I am not sent to a terminal that says the session ended.

**Why this priority**: It prevents confusion and keeps the companion session
model separate from Hermes native TUI sessions.

**Independent Test**: Navigate to a M5S3 resume URL and verify the dashboard
redirects to the companion session view with history and composer visible.

**Acceptance Scenarios**:

1. **Given** a URL contains `resume=m5s3:main-session`, **When** the dashboard
   loads, **Then** it opens the M5S3 session history instead of the TUI terminal.
2. **Given** a normal Hermes TUI session is selected, **When** the owner clicks
   resume, **Then** the original TUI resume behavior still works.

### Edge Cases

- The companion runtime is offline while the dashboard can still read history.
- The session exists in local state but the latest reply generation fails.
- The user sends an empty message with no attachment.
- The user attaches a file whose name or type cannot be trusted.
- The dashboard is running in WSL while the companion runtime is running on
  Windows localhost.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST provide a composer for M5S3 companion sessions.
- **FR-002**: Users MUST be able to send non-empty text messages into the M5S3
  companion session from the dashboard.
- **FR-003**: The system MUST persist dashboard-sent companion messages in the
  same session history as device voice turns.
- **FR-004**: The system MUST return a visible assistant reply or a visible
  failure state for each dashboard-sent text message.
- **FR-005**: The dashboard MUST display attachment metadata for sent multimedia
  messages.
- **FR-006**: The system MUST validate attachments before accepting them,
  including file count, size, name, and content type.
- **FR-007**: The dashboard MUST not route M5S3 companion sessions into the
  Hermes TUI resume terminal.
- **FR-008**: Existing Telegram, TUI, analytics, and dashboard status behavior
  MUST continue working.
- **FR-009**: The implementation MUST be testable without requiring physical
  M5S3 hardware.

### Key Entities *(include if feature involves data)*

- **Companion Dashboard Message**: A user-sent dashboard message associated with
  a companion session; includes text, optional attachments, status, timestamps,
  and generated reply.
- **Companion Attachment**: Metadata for an uploaded media item; includes file
  name, content type, size, storage reference, and validation status.
- **Companion Session**: The existing M5S3 conversation thread shown in dashboard
  history.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner can send a text message to the M5S3 session and see the
  reply in under 10 seconds during normal local runtime operation.
- **SC-002**: 100% of dashboard-sent M5S3 messages appear in the same session
  history after refresh.
- **SC-003**: Unsupported or oversized attachments are rejected before sending
  with a visible explanation.
- **SC-004**: Navigating to a M5S3 resume URL never leaves the owner on a blank
  or ended TUI terminal page.

## Assumptions

- The first implementation supports text replies as the primary interaction.
- Multimedia v1 records and displays attachment metadata; deep multimodal model
  understanding can be added later.
- The existing local companion runtime remains the owner of reply generation.
- The dashboard may proxy requests across WSL/Windows runtime boundaries.

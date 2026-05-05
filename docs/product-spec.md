# Product Spec

## Title

Personal Hermes Companion System

## Product Summary

Build a single-agent personal system with three user-facing surfaces:

- `Telegram / Talk to Hermes CEO`
- `M5Stick S3 embodied companion`
- `future Desktop UI`

The system must feel like one persistent assistant, not three disconnected bots.

## Core Product Principle

There is only one real brain.

Everything else is a surface:

- Telegram is the main control console.
- M5Stick S3 is the embodied pet-like companion.
- Desktop UI is the future rich workstation.

## User Experience Goals

### 1. Unified identity

The user should feel that all surfaces talk to the same entity.

That means:

- the same preferences apply everywhere
- tasks created from one surface are visible from another
- approvals can happen in Telegram even if the task began on M5

### 2. Embodied companionship

`M5Stick S3` should feel like a tiny companion, not a generic voice API client.

The desired feeling:

- it notices when you speak
- it reacts emotionally
- it gives short spoken replies
- it can be interrupted
- it can hand longer work off to Telegram

### 3. Separation of depth by surface

Each surface should do the work it is best at.

- `M5Stick S3`
  - short conversation
  - quick capture
  - short status
  - pet-like presence

- `Telegram`
  - planning
  - long replies
  - approvals
  - task follow-up
  - full command surface

- `Desktop UI`
  - future dense operations
  - memory review
  - job board
  - model router visibility
  - device monitoring

## Surface Specs

## Telegram

### Role

Primary control console and the main operator surface.

### Must support

- long-form chat
- create tasks
- ask for status
- approve or reject work
- receive longer results
- receive escalations from device-side interactions

### Should become the system of record for

- durable memory
- durable jobs
- approvals
- complex task state

## M5Stick S3

### Role

Pet-like embodied terminal connected to the same main agent.

### Input modes

- hold button to record
- release to send
- optional future secondary button for quick confirm/cancel

### Output modes

- facial expression on screen
- small speech bubble text
- short spoken reply
- short status cues

### State model

Device state:

- `boot`
- `idle`
- `recording`
- `uploading`
- `thinking`
- `speaking`
- `error`

Emotional overlay:

- `neutral`
- `happy`
- `curious`
- `excited`
- `sleepy`
- `sad`

### Interaction rules

- replies should usually be short
- long answers should be summarized on device and continued in Telegram
- the device should be interruptible while speaking
- failures should sound pet-like and soft, not like raw error messages

### Embodied UX requirements

- `idle`
  - blink
  - quiet presence
  - short invitation text

- `recording`
  - attentive face
  - clear listening cue
  - optional simple level meter

- `thinking`
  - obvious waiting animation
  - visible "I heard you and I am processing" state

- `speaking`
  - mouth movement or equivalent animation
  - matching short text bubble

- `error/offline`
  - soft failure expression
  - reassure that the message was cached if possible

## Desktop UI

### Role

Future rich workstation surface sharing the same brain.

### Version 1 modules

- `Agent Chat`
- `Task Board`
- `Memory Panel`
- `Companion Panel`
- `Model Router Panel`

### Companion Panel requirements

- device online/offline
- battery level
- last voice turn
- current emotion
- latest short reply

## Routing Spec

Every incoming device voice turn should be classified into one of four intents:

- `companion_chat`
- `capture_task`
- `status_query`
- `approval_action`

### Routing rules

- `companion_chat`
  - handled locally in the voice companion path
  - stays short and conversational

- `capture_task`
  - create or update a shared job in the main task system
  - return a short acknowledgment to device
  - optionally send full details to Telegram

- `status_query`
  - ask the shared job system
  - return a very short spoken answer

- `approval_action`
  - if safe and unambiguous, forward to the shared approval system
  - if ambiguous, ask the user to confirm in Telegram

## Shared Data Model

The following concepts must eventually be shared across all surfaces:

- `owner_id`
- `job_id`
- `memory_id`
- `channel_source`
- `device_id`
- `telegram_chat_id`

Minimum invariant:

- M5-created tasks must be visible in Telegram.
- Telegram-approved tasks must reflect as resolved when queried from M5.

## Model Routing Product Rules

Use OpenRouter with role-based routing:

- `auxiliary`
  - routine chat
  - summarization
  - capture structuring
  - light drafting

- `primary`
  - complex planning
  - approval-sensitive work
  - formal writing
  - long-context reasoning

- `vision`
  - reserved for future camera-capable surfaces

### Surface-specific routing

- M5 device default:
  - short chat -> `auxiliary`
  - escalated or sensitive task -> `primary`

- Telegram default:
  - normal management chat -> `auxiliary`
  - complex planning or external-facing writing -> `primary`

## Development Priorities

### Immediate

- preserve current M5 voice loop
- preserve current Telegram path
- unify identity model
- add intent routing from voice turns into the shared task system

### Next

- define forwarding protocol between local companion gateway and the main Telegram/Hermes brain
- add task handoff summaries from M5 to Telegram
- reduce duplicate memory ownership

### Later

- build desktop UI
- expose device state in desktop panel
- formalize shared owner/task/session schema

## Non-Goals For Now

- multiple independent agent brains
- full offline autonomous M5 reasoning
- long-form document review on device
- replacing Telegram as the primary control surface

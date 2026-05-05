# Architecture

## Goal

This project is the local control plane and embodiment gateway for a personal Hermes-based agent system.

It is not meant to replace Hermes itself. Instead, it provides the glue layer between:

- the main cloud or remote agent brain
- messaging channels such as Telegram or WeCom
- embodied hardware such as `M5Stick S3`
- future richer surfaces such as a desktop UI

## Current Shape

The repository already contains two partially separate runtime paths:

1. `Task agent path`
   - text ingress
   - task workflows
   - jobs
   - approval state
   - memory candidates
   - skill registry

2. `Voice companion path`
   - device voice turns
   - audio upload
   - transcription
   - short spoken reply generation
   - TTS audio return
   - short companion session history

They currently share:

- one Python service process
- one OpenRouter model adapter
- one local state store

They do **not** yet fully share:

- one unified owner identity
- one unified task pool
- one unified memory path
- one unified routing policy between chat vs task execution

## Target Architecture

The intended end state is:

- `one main agent brain`
- `multiple channel adapters`
- `multiple embodiment shells`

### Main Agent

The main agent is the only source of truth for:

- memory
- jobs
- approvals
- model routing
- durable skills
- long-form reasoning

### Channel Adapters

Channel adapters are only ingress and egress layers. They should not become separate brains.

- `Telegram`
  - primary remote control surface
  - long-form conversation
  - task management
  - approvals
  - high-density output

- `WeCom / WeChat`
  - alternate messaging ingress
  - notifications and lightweight control

- `Desktop UI`
  - future rich control surface
  - full task board, memory review, device status, routing controls

### Embodied Companion

`M5Stick S3` is an embodied terminal, not a second agent.

Its job is:

- push-to-talk voice input
- short spoken or displayed replies
- visible emotional state
- quick capture
- short status interactions

Its job is not:

- independent planning
- durable long-term memory ownership
- complex task execution logic

## Recommended Runtime Topology

```text
Telegram / Hermes CEO
        |
        v
 Main Agent Brain
 (Hermes + durable memory + jobs + approvals)
        ^
        |
 Companion Gateway (this repo)
        ^
        |
    M5Stick S3
```

In this topology:

- Telegram remains the main operator console.
- The local gateway in this repo handles device voice turns and embodied UX.
- `M5Stick S3` forwards useful intent to the main agent instead of growing into a separate brain.

## Integration Principle

The most important invariant is:

**one owner, one task pool, one memory system**

That means every surface must eventually map into a shared identity model:

- `owner_id`
- `telegram_chat_id`
- `device_id`
- optional future `desktop_session_id`

## M5Stick S3 Role

The hardware should be treated as a `pet-like embodied interface`.

### Good fit

- short voice turns
- emotional UI
- simple stateful companionship
- quick notes
- "what should I do next?" type questions

### Bad fit

- long-form reading
- dense task editing
- complex approval review
- large visual dashboards

## Desktop UI Role

The future desktop UI should become the richest surface for:

- long conversation
- task board
- memory review
- device monitoring
- model routing control
- transcript inspection

It should still use the same main agent brain.

## Current Gap To Close

The next major architecture step is to add a shared routing layer so that an incoming voice turn can become one of:

- `companion_chat`
- `capture_task`
- `status_query`
- `approval_action`

Only the first category should stay entirely inside the local companion loop.
The others should be forwarded into the main agent path.

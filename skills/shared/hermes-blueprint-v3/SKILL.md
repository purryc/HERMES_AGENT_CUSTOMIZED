---
name: hermes-blueprint-v3
description: Hermes Blueprint v3.0 - Personal AI Mission Control System architecture and implementation roadmap
version: 3.0.0
author: Hermes Agent + shino yan
tags: [Hermes, Architecture, Multi-Agent, Mission Control, System Design, Portable Brain, Device Roles]
---

# Hermes Blueprint v3.0: Personal AI Mission Control

## Core Vision

Hermes is a **Personal AI Chief of Staff** - a central orchestration layer that:
- Learns my working style and preferences
- Coordinates multiple specialist agents (Codex, Claude, Gemini, etc.)
- Routes tasks intelligently across machines
- Captures and backfills all work into persistent memory
- Evolves through approved reflection cycles
- Stays portable and device-agnostic

## Key Design Principles

1. **Reusable Methodology Across Machines** - Same workflow works on Home PC, Work Mac, future Mac mini, or any device
2. **Portable Brain** - Can migrate from one machine to another with full backup/restore
3. **Multi-Device Coordination** - Brain Server + Worker Nodes + Client + Mobile + Pocket Companion
4. **Approval-Based Safety** - High-risk actions require human approval
5. **Codex Capture & Backfill** - Even direct Codex work (not routed through Hermes) gets captured retroactively

## 9-Step Hermes Operating Loop

```
1. Mission Capture      → Create structured task
2. Context Gathering    → Collect relevant files, docs, metadata
3. Task Routing        → Decide which agent (Codex/Claude/Gemini/Worker)
4. Agent Assignment    → Bind to execution endpoint
5. Execution           → Run via model/API/CLI/local automation
6. Approval            → Pause for high-risk actions
7. Artifact Registration → Save outputs, diffs, reports
8. Reflection          → Assess quality, style match, routing correctness
9. Memory/Skill Update → Only after user approval, persist learnings
```

## Device Role Framework

Instead of hardcoding machines, classify by functional role:

| Role | Example | Responsibility |
|------|---------|-----------------|
| **Brain Server** | Mac mini / Home PC | SSOT for missions, memory, approvals, artifacts |
| **Workstation Client** | Work Mac | Main production machine, local Codex execution |
| **Worker Node** | Home PC / specialized machine | Execute delegated tasks, GPU work, automation |
| **Mobile Control** | iPhone / iPad | Remote task creation, approval, monitoring |
| **Pocket Companion** | M5Stick S3 / Raspberry Pi | Voice trigger, status alerts, quick approval |

## Current vs. Future Topology

**Current:**
```
Home PC    = Hermes Server / Brain
Work Mac   = Hermes Client / Codex Worker
iPhone     = Mobile Mission Control
M5Stick    = Pocket Companion
```

**Future:**
```
Mac mini   = Hermes Server / Brain (preferred, low-power 24x7)
Home PC    = Worker Node / Windows Operator / GPU Worker
Work Mac   = Workstation Client / Codex Worker
iPhone     = Mobile Mission Control
Raspberry Pi = Pocket Companion / Ambient Interface
```

## Codex Memory Capture Strategy

Not all work starts from Hermes. Direct Codex work should be captured retroactively.

### Capture Modes

1. **Preferred: Hermes-Routed Codex**
   - Create mission → Hermes assigns to Mac Codex Worker → stdout/diff/artifacts captured

2. **Fallback: Direct Codex + Backfill**
   - Work directly on Mac → `hcodex` or `hermes capture-codex` → Hermes records work

### Key Commands

```bash
# Wrapper command for automatic capture
hcodex "Update PPT skill layout"

# Manual backfill capture
hermes capture-codex
hermes capture-codex --summary "Updated HCI one-pager PPT skill layout"
hermes capture-codex --repo ./ppt-skill --artifact ./output.pptx
```

### Capture Maturity Levels

- **Level 1**: Manual capture via `hermes capture-codex` (MVP)
- **Level 2**: Assisted capture with watcher detecting changes + prompts
- **Level 3**: Full hcodex wrapper with automatic logging

## Mission Control Dashboard

Core pages:
- **Today** - Today's tasks, pending approvals, alerts
- **Missions** - All missions, filtered by status/priority
- **Runs** - Execution history, logs, costs
- **Approvals** - Pending high-risk actions
- **Artifacts** - Generated outputs, searchable
- **Budget** - Cost tracking per agent/week/project
- **Memory** - View/edit learned preferences
- **Skills** - Reusable workflows
- **Devices** - Status of all registered machines
- **Workflows** - Templates for common tasks

## Routing Engine Example

```yaml
routing_rules:
  email_rewrite:
    agent: openrouter_fast_model
    approval: false
    cost_max: $0.10

  deep_pdf_analysis:
    agent: gemini_analyst
    second_pass: claude_architect
    approval: false

  code_repo_task:
    agent: codex_engineer
    approval_required:
      - modify_files: true
      - install_packages: true
      - git_push: true

  mac_prototype_task:
    agent: mac_codex_worker
    runtime: codex_cli
    approval_required:
      - modify_more_than_10_files
      - install_packages

  local_operation:
    agent: openclaw_operator
    approval_required:
      - account_login
      - payment
      - file_delete
      - shell_command
```

## Approval System

Approval required for:
- File deletion / overwrite / many-file changes
- Git operations (push, rebase, etc.)
- Email sending
- High-cost model calls
- Account login / payments
- System setting changes
- Restricted folder access

Approval surfaces: Web dashboard, mobile dashboard, simplified Pocket Companion UI

## Cross-Device Sync Strategy

**Principle**: One active brain server, sync via API + files, NOT direct DB sync

- **File sync**: Syncthing for ~/HermesWorkspace (avoid node_modules, .env, secrets)
- **Event sync**: Clients write through Hermes APIs (POST /api/runs, /api/memory, etc.)
- **Workspace structure**:
  ```
  ~/HermesWorkspace/
  ├─ 00_inbox/           # Quick capture
  ├─ 01_projects/        # Active work
  ├─ 02_skills/          # Reusable templates
  ├─ 03_memory/          # Exported memory
  ├─ 04_artifacts/       # Generated outputs
  ├─ 05_prompts/         # System prompts
  └─ 99_archive/
  ```

## Core Data Model

Key entities:
- `missions` - Structured tasks
- `runs` - Execution records (agent, device, tools, cost, status)
- `artifacts` - Outputs (files, diffs, reports, PPTs)
- `approvals` - Pending high-risk actions
- `memory` - Learned preferences (playbooks, rubrics, style rules)
- `skills` - Reusable workflows
- `devices` - Registered machines
- `reflections` - Assessment of past work
- `workflow_templates` - Portable methodologies

## Memory System

**Complete memory architecture:** See `references/memory-system-architecture.md` for four-layer design (Hard/Evolving/Episodic/Context), storage strategy across GitHub/DB/Syncthing/rclone, and multi-project parallel execution.

Core concept: Not just chat storage, but working method learning:

- **Thinking Playbooks**: HCI paper analysis, Patent mining, PPT structure, Trend analysis
- **Decision Rubrics**: Feature vs platform? Patent potential? Roadmap fit? Codex vs Claude?
- **Style Memory**: High density, white background, gray-red style, card-based, PPT-ready
- **Routing Memory**: Emails→OpenRouter, Strategy→Claude, PDFs→Gemini, Code→Codex
- **Workflow Templates**: HCI paper→one-pager, Repo analysis→arch doc, PPT skill update

## Self-Evolution Reflection Loop

After each run, Hermes reflects:
```
Compare output to user edits
→ What was edited? Why?
→ What preference did that reveal?
→ Should style_memory update?
→ Should routing rules improve?
→ Should skill template evolve?
→ User approves → Persistent update
```

This is how Hermes learns to work like you.

## Portable Brain: Migration Plan

### Current Setup
- Home PC = Server
- Work Mac = Client/Codex Worker
- Phone = Mobile Control
- M5Stick = Pocket Companion

### Target Setup (Post-Mac Mini Migration)
- Mac mini = Server (preferred long-term)
- Home PC = Worker Node / GPU Worker
- Work Mac = Client / Codex Worker
- Phone = Mobile Control
- Raspberry Pi = Pocket Companion

### Migration Requirements
```bash
hermes backup                    # Full backup
hermes restore <backup_id>      # Restore on new machine
hermes export-memory            # Portable memory
hermes import-memory <file>     # Load on new machine
hermes reindex                   # Rebuild indexes
hermes register-device          # Re-register all devices
hermes migrate-server           # Switch primary brain
```

## Implementation Roadmap (13 Weeks)

### Week 1-2: Core Capture System
- hcodex wrapper script (auto-logging Codex calls)
- Run log database table
- hermes capture-codex command
- Device role framework + registration

### Week 3-4: Mission Control Dashboard
- Today / Missions / Runs / Approvals pages
- Budget tracking
- Artifact viewer
- Search + filter

### Week 5-6: Cross-Device Sync
- Syncthing setup guide
- File watcher with indexing
- API-based sync (no direct DB sync)
- Offline queue + conflict resolution

### Week 7-8: Reflection Engine
- Auto-generate reflection questions
- Memory/Skill update suggestions
- User approval workflow
- Versioning + rollback

### Week 9-10: Full Integration
- Complete Mission dashboard
- Multi-agent routing working
- Hermes learning active preferences

### Week 11-12: Portable Brain
- Backup/restore tools
- Mac mini setup guide
- Complete migration test
- Device re-registration flow

### Week 13: Buffer + Optimization

## Reusable Onboarding for New Machines

Any new machine should follow standard steps:
```
1. Register device + assign role
2. Define allowed actions + approval thresholds
3. Sync HermesWorkspace (Syncthing)
4. Sync workflow templates
5. Apply policy + security rules
6. Run health check
7. Test sample mission
8. Validate artifact logging
9. Add to active device registry
```

This makes Hermes a portable operating methodology, not a one-off setup.

## Final Vision

```
Hermes = Your personal AI Chief of Staff
- Knows your working style (learned, not programmed)
- Coordinates specialist agents (Codex, Claude, Gemini, etc.)
- Remembers decisions and builds reusable workflows
- Stays portable across machines via portable brain
- Gets smarter through approved reflection
- Keeps you in control via approval gates
- Captures all work, even direct Codex sessions
```

One-liner: **Central orchestration + persistent learning + multi-device + approval-safe + portable methodology**

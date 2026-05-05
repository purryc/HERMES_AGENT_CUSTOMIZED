<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- [PRINCIPLE_1_NAME] -> User-Visible Companion Loop
- [PRINCIPLE_2_NAME] -> Local-First Control Surface
- [PRINCIPLE_3_NAME] -> Testable Routing and Persistence
- [PRINCIPLE_4_NAME] -> Safe Desktop and Browser Actions
- [PRINCIPLE_5_NAME] -> Small, Reversible Integrations
Added sections:
- Runtime Constraints
- Development Workflow
Removed sections:
- Template placeholder sections
Templates requiring updates:
- .specify/templates/plan-template.md: no change required
- .specify/templates/spec-template.md: no change required
- .specify/templates/tasks-template.md: no change required
Follow-up TODOs: none
-->
# Hermes Personal Agent Constitution

## Core Principles

### I. User-Visible Companion Loop
Every companion-facing feature MUST make its current state visible to the user:
received, processing, completed, failed, or awaiting approval. A command path is
not complete until the user can see what happened in the relevant surface, such
as the M5 device, dashboard session history, or desktop browser.

### II. Local-First Control Surface
Local dashboard and device controls MUST prefer the user's local agent runtime
and local persisted state before relying on external services. Remote tunnels
and external brains may extend capability, but the system must degrade clearly
when they are unreachable.

### III. Testable Routing and Persistence
New message, intent, and automation routes MUST include deterministic tests for
classification, persistence, and the returned user-visible result. Stored
records must be readable by the dashboard without requiring hidden side effects.

### IV. Safe Desktop and Browser Actions
Actions that affect the user's computer, browser, accounts, files, or external
messages MUST be explicit, bounded, and auditable. Read-only navigation and
search may run directly when requested; destructive, credential, payment, or
external-send actions require confirmation.

### V. Small, Reversible Integrations
Integrations with upstream Hermes dashboard code, firmware, or companion
protocols MUST stay narrow and reversible. Prefer additive adapters and feature
specific endpoints over broad rewrites, and document any patch applied outside
the repository root.

## Runtime Constraints

The project spans a Windows local agent, a WSL-hosted Hermes dashboard, and
ESP32-S3 firmware. Features MUST state which runtime owns each behavior and how
data crosses runtime boundaries. Local SQLite state remains the source of truth
for companion sessions unless a feature explicitly migrates it.

## Development Workflow

Non-trivial features, bug fixes, and refactors MUST follow the Spec Kit flow:
specification, clarification when needed, implementation plan, tasks, optional
analysis, and implementation. Tiny diagnostics or emergency patches may skip the
full workflow only when the scope and risk are explicitly stated.

## Governance

This constitution supersedes ad-hoc development preferences for this repository.
Changes require updating this file, recording the version impact, and checking
that templates or runtime guidance still align. Semantic versioning applies:
MAJOR for incompatible governance changes, MINOR for new principles or sections,
and PATCH for clarifications.

**Version**: 1.0.0 | **Ratified**: 2026-04-30 | **Last Amended**: 2026-04-30

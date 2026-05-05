<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
specs/003-vercel-remote-dashboard/plan.md
<!-- SPECKIT END -->

# Shared Agent Memory

Before substantial work in this workspace, read
`memory/SHARED_AGENT_MEMORY.md`. It is the shared memory bridge between Codex
and Hermes Agent.

If the task creates durable user preferences, long-lived project decisions, or
cross-agent handoff notes, update `memory/SHARED_AGENT_MEMORY.md` at the end of
the task. Do not store API keys, bot tokens, passwords, recovery codes, or
one-time login codes in shared memory.

# Development Process

All future feature work, non-trivial changes, refactors, and bug fixes must go
through the Spec Kit workflow before implementation:

1. Establish or update project principles with `$speckit-constitution`.
2. Create or update the feature specification with `$speckit-specify`.
3. Resolve important ambiguities with `$speckit-clarify` when requirements are
   unclear.
4. Create the technical plan with `$speckit-plan`.
5. Break the plan into actionable tasks with `$speckit-tasks`.
6. Optionally run `$speckit-analyze` for cross-artifact consistency before
   implementation.
7. Implement with `$speckit-implement`.

For tiny mechanical edits, documentation typo fixes, or emergency diagnostics,
state why the full workflow is unnecessary and keep the change scoped.

# Implementation Plan: Vercel Remote Dashboard MVP

**Branch**: `003-vercel-remote-dashboard` | **Date**: 2026-05-05 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/003-vercel-remote-dashboard/spec.md`

## Summary

Create a thin Vercel-hosted remote dashboard for quick validation. The UI is a
small Vite/React app under `remote-dashboard`; Vercel serverless functions proxy
approved requests to a Cloudflare Tunnel URL. The tunnel points to a local
standard-library Python guard on Windows, and the guard forwards only approved
paths to the existing local Hermes Agent at `127.0.0.1:8787`.

## Technical Context

**Language/Version**: TypeScript/React 19, Vite 7, Node 22; Python 3.10 standard library for the local guard  
**Primary Dependencies**: Vercel serverless functions, Cloudflare `cloudflared`, existing Hermes local HTTP API  
**Storage**: No remote storage; local ignored tunnel state in `data/`  
**Testing**: `npm run build` for remote dashboard; Python `unittest` for guard path/auth behavior; manual local tunnel smoke test when cloudflared is available  
**Target Platform**: Vercel frontend/functions plus Windows local Hermes worker  
**Project Type**: Web app plus local helper scripts  
**Performance Goals**: Health check within 5 seconds; companion text turn result visible within 20 seconds under normal tunnel conditions  
**Constraints**: Do not expose raw local Hermes API; do not support arbitrary local file/Codex/browser operations in MVP; avoid committing tokens/state  
**Scale/Scope**: Single-user remote access MVP for health + M5S3 text chat

## Constitution Check

- User-Visible Companion Loop: PASS. The remote page shows health, send status, and reply text.
- Local-First Control Surface: PASS. Hermes/Codex execution stays on the local machine.
- Testable Routing and Persistence: PASS. Guard auth/path rules and dashboard build are testable.
- Safe Desktop and Browser Actions: PASS. MVP does not expose desktop/browser/Codex execution APIs.
- Small, Reversible Integrations: PASS. New subproject and scripts are additive.

## Project Structure

### Documentation (this feature)

```text
specs/003-vercel-remote-dashboard/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- remote-dashboard.md
`-- tasks.md
```

### Source Code

```text
remote-dashboard/
|-- api/hermes/[...path].ts
|-- src/App.tsx
|-- src/main.tsx
|-- src/styles.css
|-- index.html
|-- package.json
|-- tsconfig.json
|-- vite.config.ts
`-- .env.example

scripts/
|-- hermes_tunnel_guard.py
|-- start-hermes-cloudflare-tunnel.ps1
`-- stop-hermes-cloudflare-tunnel.ps1

tests/
`-- test_tunnel_guard.py

docs/
`-- vercel-remote-dashboard.md
```

**Structure Decision**: Keep the Vercel app isolated in `remote-dashboard` so
Vercel can use it as the root directory. Keep local tunnel tooling in `scripts`
and tests in the existing Python test area.

## Complexity Tracking

No constitution violations.

# Implementation Plan: Portrait Companion UI

**Branch**: `001-portrait-companion-ui` | **Date**: 2026-04-30 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/001-portrait-companion-ui/spec.md`

## Summary

Replace the current horizontal pet face UI with a portrait-oriented cyber companion interface for the M5Stick S3 firmware. The implementation keeps the existing voice state machine intact and changes only the drawing layer: display rotation, avatar rendering, HUD frame, message panel, and state-driven animated expressions.

## Technical Context

**Language/Version**: Arduino C++ for ESP32-S3  
**Primary Dependencies**: M5Unified, M5GFX, ArduinoJson, WiFi/HTTP libraries  
**Storage**: SPIFFS for pending audio queue; no new storage for this feature  
**Testing**: PlatformIO build check; manual device verification after flashing  
**Target Platform**: M5Stick S3 / ESP32-S3 small color display  
**Project Type**: Embedded firmware  
**Performance Goals**: UI refresh remains non-blocking at the existing refresh cadence  
**Constraints**: Small screen, limited heap, no large bitmap assets, existing voice workflow must remain unchanged  
**Scale/Scope**: One firmware target under `firmware/m5sticks3_pet`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution is still in template form, so there are no enforceable project-specific gates beyond the repository-level Spec Kit workflow. This plan follows the required specify -> plan -> tasks -> implement sequence.

## Project Structure

### Documentation (this feature)

```text
specs/001-portrait-companion-ui/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- checklists/
|   `-- requirements.md
`-- tasks.md
```

### Source Code (repository root)

```text
firmware/
`-- m5sticks3_pet/
    |-- include/
    |   `-- pet_config.h
    |-- platformio.ini
    `-- src/
        `-- main.cpp
```

**Structure Decision**: Implement the UI in the existing single firmware source file because the current UI, device state, and expression state already live together in `firmware/m5sticks3_pet/src/main.cpp`. Avoid new asset files to preserve flash and memory.

## Complexity Tracking

No constitution violations or additional complexity are introduced.

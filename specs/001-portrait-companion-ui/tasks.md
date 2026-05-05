# Tasks: Portrait Companion UI

**Input**: Design documents from `specs/001-portrait-companion-ui/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm target files and constraints before changing firmware drawing.

- [x] T001 Review existing UI state and draw functions in `firmware/m5sticks3_pet/src/main.cpp`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish portrait layout helpers used by all visual states.

- [x] T002 Update display orientation and text wrapping assumptions in `firmware/m5sticks3_pet/src/main.cpp`
- [x] T003 Implement reusable HUD and panel drawing helpers in `firmware/m5sticks3_pet/src/main.cpp`

---

## Phase 3: User Story 1 - Vertical Cyber Companion (Priority: P1) MVP

**Goal**: Device shows a vertical cyber female companion as the primary UI.

**Independent Test**: Build firmware and verify the first rendered UI is portrait-oriented with avatar, HUD, and message panel.

- [x] T004 [US1] Replace the simple pet face renderer with a portrait companion renderer in `firmware/m5sticks3_pet/src/main.cpp`
- [x] T005 [US1] Recompose `drawUi()` into top status, central avatar, and bottom message panel in `firmware/m5sticks3_pet/src/main.cpp`

---

## Phase 4: User Story 2 - State-Based Animated Expressions (Priority: P2)

**Goal**: Distinct animated expressions communicate assistant states.

**Independent Test**: Trigger idle, listening, thinking, speaking, error, and sleepy states and verify distinct facial or HUD animation cues.

- [x] T006 [US2] Add expression rendering for idle, listening, thinking, speaking, error, happy, curious, sleepy, and excited states in `firmware/m5sticks3_pet/src/main.cpp`
- [x] T007 [US2] Add non-blocking blink, pulse, scanline, and speaking mouth animation based on `millis()` in `firmware/m5sticks3_pet/src/main.cpp`

---

## Phase 5: User Story 3 - Compact Text Panel (Priority: P3)

**Goal**: Assistant text stays readable in the new portrait layout.

**Independent Test**: Verify normal and long bubble text fits in the bottom panel without overlap.

- [x] T008 [US3] Adjust message text splitting and truncation for portrait lower panel in `firmware/m5sticks3_pet/src/main.cpp`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate and record the completed implementation.

- [x] T009 Run PlatformIO build for `firmware/m5sticks3_pet`
- [x] T010 Mark completed tasks in `specs/001-portrait-companion-ui/tasks.md`

---

## Phase 7: User Story 4 - Shake Dizzy Expression (Priority: P3)

**Goal**: Firmly shaking the device briefly makes the companion look dizzy without interrupting voice workflows.

**Independent Test**: Shake the S3 Stick while idle and while speaking; verify dizzy animation appears briefly and clears automatically.

- [x] T011 [US4] Add IMU shake gesture detection in `firmware/m5sticks3_pet/src/main.cpp`
- [x] T012 [US4] Add temporary dizzy face and HUD animation overlay in `firmware/m5sticks3_pet/src/main.cpp`

---

## Phase 8: Flicker Fix

**Goal**: Keep the animated portrait UI stable on the physical screen.

**Independent Test**: Watch the device after boot and verify the UI no longer clears to black between frames.

- [x] T013 Add M5Canvas-backed offscreen rendering in `firmware/m5sticks3_pet/src/main.cpp`
- [x] T014 Remove full-width scanline animation from `firmware/m5sticks3_pet/src/main.cpp`

---

## Phase 9: Chinese Text Vertical Scroll

**Goal**: Keep Chinese and long assistant replies readable in the lower panel.

**Independent Test**: Display a long Chinese reply and verify the panel shows two lines at a time, then scrolls vertically through complete characters without square glyphs caused by broken UTF-8 truncation.

- [x] T015 Replace byte-based bubble text splitting with UTF-8 preserving normalization in `firmware/m5sticks3_pet/src/main.cpp`
- [x] T016 Add clipped two-line vertical scroll rendering for long text in `firmware/m5sticks3_pet/src/main.cpp`

## Dependencies & Execution Order

- Phase 1 must complete before firmware edits.
- Phase 2 must complete before user story rendering changes.
- User Story 1 should complete before User Story 2 and User Story 3.
- Polish runs after all selected user stories are complete.

## Implementation Strategy

Deliver the MVP first by switching to portrait layout and drawing the companion avatar, then layer state-based expressions and finally verify text fit.

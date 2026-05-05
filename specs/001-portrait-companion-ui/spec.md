# Feature Specification: Portrait Companion UI

**Feature Branch**: `001-portrait-companion-ui`  
**Created**: 2026-04-30  
**Status**: Draft  
**Input**: User description: "读取我S3 STICK的代码，我想改下UI， 改成竖屏的美女形象，然后帮我设计几个相应的动画表情"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vertical Cyber Companion (Priority: P1)

As the device owner, I want the S3 Stick screen to show a portrait-oriented cyber-style female companion instead of the previous simple pet face, so the assistant feels closer to the provided visual reference.

**Why this priority**: The visual identity is the main requested change and should be visible immediately after boot.

**Independent Test**: Flash or build the firmware and verify the first screen uses a vertical portrait composition with a female avatar, cyan HUD framing, status text, and a lower message panel.

**Acceptance Scenarios**:

1. **Given** the device has booted, **When** it enters idle mode, **Then** the screen shows a portrait female companion in a vertical cyber frame.
2. **Given** WiFi and battery data are available, **When** the UI refreshes, **Then** status information remains readable without covering the avatar.

---

### User Story 2 - State-Based Animated Expressions (Priority: P2)

As the device owner, I want the companion to show distinct animated expressions for idle, listening, thinking, speaking, error, and sleepy/offline states, so the assistant communicates its state without relying only on text.

**Why this priority**: Animated expressions make the device feel alive and help users understand state changes at a glance.

**Independent Test**: Trigger each state and verify the avatar changes eyes, mouth, accent effects, or motion cues within the same portrait layout.

**Acceptance Scenarios**:

1. **Given** the user holds Button A, **When** recording starts, **Then** the companion shifts into an attentive listening expression with recording cues.
2. **Given** the assistant is processing, **When** the state is thinking, **Then** the UI shows a contemplative expression and animated HUD activity.
3. **Given** the assistant is playing audio, **When** speaking starts, **Then** the mouth animates to indicate speech.
4. **Given** an upload or playback error occurs, **When** the error state is active, **Then** the expression becomes visibly sad or concerned.

---

### User Story 3 - Compact Text Panel (Priority: P3)

As the device owner, I want the assistant's short messages to remain readable inside a compact sci-fi panel, so the visual upgrade does not reduce usability.

**Why this priority**: The device still needs to show prompts and brief responses clearly on a small screen.

**Independent Test**: Feed short and long bubble text and verify it wraps into the lower panel without overlapping the avatar or status area.

**Acceptance Scenarios**:

1. **Given** a short prompt is displayed, **When** the UI refreshes, **Then** it fits inside the lower panel.
2. **Given** a long response is displayed, **When** the UI refreshes, **Then** it scrolls through the lower panel without overlapping other UI elements.
3. **Given** a Chinese response is displayed, **When** the UI refreshes, **Then** complete UTF-8 characters are preserved instead of being cut into broken glyphs.

---

### User Story 4 - Shake Dizzy Expression (Priority: P3)

As the device owner, I want the companion to become dizzy when I shake the S3 Stick, so the character feels playful and physically responsive.

**Why this priority**: Shake feedback adds personality without changing the core voice workflow.

**Independent Test**: Shake the device while the assistant UI is visible and verify the avatar briefly shows a dizzy expression, then returns to its previous state display.

**Acceptance Scenarios**:

1. **Given** the assistant UI is visible, **When** the device is shaken firmly, **Then** the avatar shows a dizzy face with motion cues for a short duration.
2. **Given** the dizzy animation is active, **When** recording, thinking, or speaking continues, **Then** the underlying workflow continues without interruption.
3. **Given** the device is moved gently, **When** acceleration stays below the shake threshold, **Then** the dizzy expression does not trigger accidentally.

### Edge Cases

- If WiFi is disconnected, the avatar should remain visible and use a subdued or sleepy/offline expression.
- If the battery value is unavailable or low, status text should remain readable in the top HUD.
- If a response contains newline characters or long text, the message panel should normalize and truncate the content.
- If the device is shaken repeatedly, the dizzy expression should not retrigger so often that the rest of the UI becomes unusable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The device MUST use a vertical screen orientation for the companion UI.
- **FR-002**: The UI MUST display a cyber-style female companion avatar as the primary visual element.
- **FR-003**: The UI MUST preserve readable WiFi, state, and battery indicators.
- **FR-004**: The UI MUST provide distinct visual expressions for idle, listening, thinking, speaking, error, happy, curious, sleepy, and excited moods where applicable.
- **FR-005**: The UI MUST animate expressions or HUD details over time without blocking recording, upload, polling, or playback behavior.
- **FR-006**: The UI MUST retain a compact message panel for the assistant prompt or reply text.
- **FR-007**: The UI MUST fit all visual elements on the S3 Stick display without overlapping text and avatar elements.
- **FR-008**: The device MUST detect a firm shake gesture and temporarily show a dizzy expression without changing the current voice workflow state.
- **FR-009**: Long message text MUST scroll in the lower panel and MUST NOT split multibyte Chinese characters.

### Key Entities

- **Companion Avatar**: The on-screen character, including face shape, hair, eyes, mouth, accessories, and HUD accent effects.
- **Expression State**: The visual mood derived from the current device state and emotion values.
- **Shake Gesture**: A short physical movement pattern that temporarily overlays the dizzy expression.
- **Message Panel**: The lower text area that displays current assistant prompt, error, or reply text.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can identify the assistant state visually within 2 seconds for idle, listening, thinking, speaking, and error states.
- **SC-002**: The UI refreshes continuously without adding noticeable delay to button-driven recording.
- **SC-003**: The portrait avatar, status indicators, and message panel fit within the visible display area in all supported states.
- **SC-004**: At least six distinct animated expression designs are available and mapped to device states or emotions.
- **SC-005**: A firm shake triggers a dizzy expression within 500 ms and clears automatically within 3 seconds.
- **SC-006**: A long Chinese response can be read by waiting for the lower panel's two-line vertical scroll to complete at least one pass.

## Assumptions

- The target device is the existing M5StickC S3-style firmware project under `firmware/m5sticks3_pet`.
- The UI should be implemented with lightweight on-device drawing primitives instead of storing large bitmap assets.
- The provided image is a style reference, not a requirement for exact reproduction.
- Existing voice recording, upload, polling, and playback behavior should remain unchanged.

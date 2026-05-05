# Data Model: Portrait Companion UI

## Companion Avatar

- **Purpose**: Represents the visible assistant persona on the device screen.
- **Attributes**: Face outline, hair volume, eyes, mouth, neckline, accessory detail, HUD accents.
- **Validation Rules**: Must fit in the portrait display area without covering status or message text.

## Expression State

- **Purpose**: Maps device state and emotion to visible expression.
- **Attributes**: Eye mode, mouth mode, accent color, pulse intensity, optional motion cue, optional temporary overlay.
- **State Transitions**: Boot/Idle -> Recording -> Uploading/Thinking -> Speaking -> Idle; Error returns to Idle after timeout.

## Shake Gesture

- **Purpose**: Represents a firm physical shake that temporarily overrides the visual expression.
- **Attributes**: Last acceleration sample, current acceleration delta, trigger timestamp, cooldown timestamp.
- **Validation Rules**: Must be ignored when movement is gentle; must expire automatically without changing the underlying device state.

## Message Panel

- **Purpose**: Displays current prompt, error, or reply text.
- **Attributes**: Normalized text, first line, second line, panel accent color.
- **Validation Rules**: Up to two visible lines; overflow is truncated with ellipsis.

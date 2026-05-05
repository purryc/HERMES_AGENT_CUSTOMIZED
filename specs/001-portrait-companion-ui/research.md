# Research: Portrait Companion UI

## Decision: Use Lightweight Primitive Drawing

**Rationale**: The existing firmware already uses M5GFX primitives. Drawing the companion with shapes, arcs, lines, and filled polygons avoids large bitmap storage, keeps memory predictable, and allows state-driven animation.

**Alternatives considered**: Bitmap sprites were rejected because the reference image style would require multiple frames and higher storage use. A full sprite pipeline can be added later if richer art becomes necessary.

## Decision: Portrait Rotation

**Rationale**: The requested UI is vertical. The display should use portrait rotation and lay out status at the top, avatar in the middle, and text panel at the bottom.

**Alternatives considered**: Keeping landscape orientation would preserve the old layout but would not match the user's requested portrait visual direction.

## Decision: Animation by State and Time

**Rationale**: Existing globals already expose `gState`, `gEmotion`, `gExpression`, and `millis()`. Expressions can be animated by deriving blink, pulse, scanline, and speaking mouth shapes from time without blocking the loop.

**Alternatives considered**: Adding animation timers or a dedicated UI state object was rejected for this scoped firmware change.

## Decision: Detect Shake from Acceleration Delta

**Rationale**: The M5Unified IMU API exposes accelerometer values in the main loop. Comparing the current acceleration to the previous sample gives a lightweight shake signal without extra dependencies or blocking work.

**Alternatives considered**: Gyroscope-based gesture recognition was rejected for this increment because acceleration delta is simpler, sufficient for a playful shake trigger, and easier to tune on-device.

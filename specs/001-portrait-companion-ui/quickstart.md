# Quickstart: Portrait Companion UI

## Build Check

```powershell
pio run -d firmware/m5sticks3_pet
```

## Manual Verification

1. Flash the firmware to the S3 Stick.
2. Confirm the screen is portrait-oriented.
3. Confirm idle mode shows the cyber female companion, top status HUD, and lower text panel.
4. Hold Button A and confirm the listening expression and recording cue appear.
5. Release Button A and confirm uploading/thinking uses a different animated expression.
6. Let playback start and confirm the speaking mouth animates.
7. Disable WiFi or force a failed upload and confirm the error/sleepy expression remains readable.
8. Shake the device firmly and confirm the companion shows a dizzy expression for a short moment, then returns to the prior state.

# Quickstart: Dashboard Companion Chat

1. Start the local agent on `0.0.0.0:8787` so local browser and WSL-hosted
   dashboard paths can both reach it.
2. Start the Hermes dashboard on `127.0.0.1:9119`. If WSL cannot reach the
   Windows host port directly, set `HERMES_M5_COMPANION_AGENT_BASE_URL` to the
   active tunnel URL before starting the dashboard.
3. Open `http://127.0.0.1:9119/sessions`.
4. Expand `M5S3 Companion Voice Session`.
5. Type `你好，从 dashboard 继续聊` in the companion composer and send.
6. Verify the new user message and assistant reply appear in the expanded
   M5S3 history after the send completes.
7. Refresh the page and verify the dashboard-sent turn is still visible.
8. Try sending an empty message with no attachment and verify it is rejected.

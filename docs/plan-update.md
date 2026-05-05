# Plan Update

## What Changed

The workspace is currently a local starter project, not the official `nousresearch/hermes-agent` repository.

That means the practical plan should be:

1. Keep this starter as the local control plane and verify the OpenRouter path.
2. Use the existing `/api/messages/wechat` endpoint as the current local message ingress.
3. Decide whether the real messaging target should be:
   - `WeCom webhook/callback` for a stable enterprise-style path, or
   - official Hermes `Weixin/iLink` integration later.
4. Only after the local control plane is stable, replace mocked or simplified edges with real Hermes gateway integrations.

## Current Status

- Local tests pass.
- OpenRouter live call works when `OPENROUTER_API_KEY` is set.
- The project now auto-loads `.env` files, so local startup is simpler.
- `scripts/start-local.ps1` starts the service.
- `scripts/send-wechat-sample.ps1` sends a local simulated WeChat message to the API.
- Real WeCom callback support is now implemented for URL verification and encrypted POST delivery.

## Recommended Next Step

Run the local service with a real `OPENROUTER_API_KEY` and WeCom secrets, then configure the self-built WeCom app callback URL:

- Callback URL: `https://your-domain.example/api/wecom/callback`
- Required secrets: `WECOM_TOKEN`, `WECOM_ENCODING_AES_KEY`, `WECOM_CORP_ID`
- Optional: `WECOM_AGENT_ID`

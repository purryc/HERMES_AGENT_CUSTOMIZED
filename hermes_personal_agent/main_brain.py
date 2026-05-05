from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import urllib.error
import urllib.request

from hermes_personal_agent.config import MainBrainConfig


class MainBrainError(RuntimeError):
    pass


@dataclass
class MainBrainResult:
    ok: bool
    owner_id: str
    remote_job_id: str
    status: str
    short_reply: str
    long_reply_text: str
    long_reply_url: str
    needs_followup: bool
    remote_request_id: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MainBrainResult":
        return cls(
            ok=bool(payload.get("ok", False)),
            owner_id=str(payload.get("owner_id", "")).strip(),
            remote_job_id=str(payload.get("remote_job_id", "")).strip(),
            status=str(payload.get("status", "")).strip(),
            short_reply=str(payload.get("short_reply", "")).strip(),
            long_reply_text=str(payload.get("long_reply_text", "")).strip(),
            long_reply_url=str(payload.get("long_reply_url", "")).strip(),
            needs_followup=bool(payload.get("needs_followup", False)),
            remote_request_id=str(payload.get("remote_request_id", "")).strip(),
        )


class MainBrainAdapter:
    def __init__(self, config: MainBrainConfig) -> None:
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.is_configured

    def forward_intent(
        self,
        *,
        intent: str,
        transcript: str,
        payload: dict[str, Any],
    ) -> MainBrainResult:
        if not self.enabled:
            raise MainBrainError("Main brain integration is disabled.")

        body = {
            "intent": intent,
            "transcript": transcript,
            "owner_id": payload.get("owner_id") or self.config.owner_id,
            "telegram_chat_id": payload.get("telegram_chat_id") or self.config.telegram_chat_id,
            "device_id": payload.get("device_id", ""),
            "session_id": payload.get("session_id", ""),
            "conversation_id": payload.get("conversation_id", ""),
            "battery_level": payload.get("battery_level"),
            "turn_id": payload.get("turn_id", ""),
            "remote_job_id": payload.get("remote_job_id", ""),
            "metadata": payload.get("metadata", {}),
        }
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.auth_token:
            headers[self.config.auth_header_name] = self.config.auth_token
        request = urllib.request.Request(
            f"{self.config.base_url}/api/companion/intents",
            data=encoded,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise MainBrainError(f"Main brain request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise MainBrainError("Main brain returned invalid JSON.") from exc

        result = MainBrainResult.from_dict(raw)
        if not result.ok:
            raise MainBrainError(raw.get("error", "Main brain returned an unsuccessful response."))
        return result

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import os


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_optional_quotes(value.strip())
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class ModelProfile:
    provider: str
    model: str
    base_url: str
    api_key_env: str
    timeout_seconds: int


@dataclass
class WeComCallbackConfig:
    token: str
    encoding_aes_key: str
    corp_id: str
    agent_id: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(
            self.token
            and self.corp_id
            and len(self.encoding_aes_key) == 43
            and not self.encoding_aes_key.startswith("replace-with-")
        )


@dataclass
class VoiceRuntimeConfig:
    api_base_url: str
    api_key: str
    transcription_model: str
    transcription_language: str
    tts_model: str
    tts_voice: str
    tts_instructions: str
    tts_device_voice: str
    tts_device_instructions: str
    tts_speed: float
    tts_output_sample_rate: int
    max_context_turns: int
    audio_ttl_seconds: int
    cleanup_interval_seconds: int


@dataclass
class MainBrainConfig:
    enabled: bool
    base_url: str
    auth_header_name: str
    auth_token: str
    owner_id: str
    telegram_chat_id: str
    timeout_seconds: int

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.base_url)


class AgentConfig:
    def __init__(self, raw: dict[str, Any], path: Path | None = None) -> None:
        self.raw = raw
        self.path = path

    @property
    def agent_name(self) -> str:
        return self.raw.get("agent_name", "Hermes Personal Work Agent")

    @property
    def data_dir(self) -> Path:
        value = self.raw.get("data_dir", "data")
        path = Path(value)
        if not path.is_absolute() and self.path:
            return (self.path.parent / path).resolve()
        return path.resolve()

    @property
    def server_host(self) -> str:
        return self.raw.get("server", {}).get("host", "127.0.0.1")

    @property
    def server_port(self) -> int:
        return int(self.raw.get("server", {}).get("port", 8787))

    @property
    def approval_risks(self) -> list[str]:
        return list(self.raw.get("approvals", {}).get("high_risk_actions", []))

    def _resolve_secret(self, block: dict[str, Any], key: str, default_env: str) -> str:
        env_name = str(block.get(f"{key}_env", default_env)).strip() or default_env
        env_value = os.getenv(env_name, "").strip()
        if env_value:
            return env_value
        return str(block.get(key, "")).strip()

    def apply_env_files(self) -> None:
        candidates: list[Path] = []
        configured = self.raw.get("env_files", [])
        if isinstance(configured, str):
            configured = [configured]

        for item in configured:
            env_path = Path(item)
            if not env_path.is_absolute() and self.path:
                env_path = (self.path.parent / env_path).resolve()
            candidates.append(env_path)

        default_candidates = [Path.cwd() / ".env"]
        if self.path:
            default_candidates.append(self.path.parent / ".env")
            if self.path.parent.parent != self.path.parent:
                default_candidates.append(self.path.parent.parent / ".env")

        seen: set[Path] = set()
        for candidate in candidates + default_candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            load_env_file(resolved)

    @property
    def wecom_callback(self) -> WeComCallbackConfig:
        block = self.raw.get("wecom", {})
        return WeComCallbackConfig(
            token=self._resolve_secret(block, "token", "WECOM_TOKEN"),
            encoding_aes_key=self._resolve_secret(block, "encoding_aes_key", "WECOM_ENCODING_AES_KEY"),
            corp_id=self._resolve_secret(block, "corp_id", "WECOM_CORP_ID"),
            agent_id=self._resolve_secret(block, "agent_id", "WECOM_AGENT_ID"),
        )

    def model_profile(self, name: str) -> ModelProfile:
        block = self.raw.get("model_router", {}).get(name, {})
        return ModelProfile(
            provider=block.get("provider", "openrouter"),
            model=block.get("model", ""),
            base_url=block.get(
                "base_url",
                "https://openrouter.ai/api/v1/chat/completions",
            ),
            api_key_env=block.get("api_key_env", "OPENROUTER_API_KEY"),
            timeout_seconds=int(block.get("timeout_seconds", 45)),
        )

    @property
    def voice_runtime(self) -> VoiceRuntimeConfig:
        block = self.raw.get("voice", {})
        return VoiceRuntimeConfig(
            api_base_url=str(block.get("api_base_url", "https://openrouter.ai/api/v1")).rstrip("/"),
            api_key=self._resolve_secret(block, "api_key", "OPENROUTER_API_KEY"),
            transcription_model=str(block.get("transcription_model", "openai/gpt-audio")),
            transcription_language=str(block.get("transcription_language", "zh")),
            tts_model=str(block.get("tts_model", "openai/gpt-4o-mini-tts-2025-12-15")),
            tts_voice=str(block.get("tts_voice", "alloy")),
            tts_instructions=str(block.get("tts_instructions", "Speak warmly in concise Mandarin Chinese.")),
            tts_device_voice=str(block.get("tts_device_voice", block.get("tts_voice", "nova"))),
            tts_device_instructions=str(
                block.get(
                    "tts_device_instructions",
                    (
                        "Speak in standard Mainland Mandarin Chinese with very clear pronunciation. "
                        "Use short phrases, slow pace, and natural pauses. "
                        "Avoid English accent, avoid code-switching, and do not sound rushed."
                    ),
                )
            ),
            tts_speed=float(block.get("tts_speed", 0.9)),
            tts_output_sample_rate=int(block.get("tts_output_sample_rate", 24000)),
            max_context_turns=int(block.get("max_context_turns", 6)),
            audio_ttl_seconds=int(block.get("audio_ttl_seconds", 900)),
            cleanup_interval_seconds=int(block.get("cleanup_interval_seconds", 60)),
        )

    @property
    def main_brain(self) -> MainBrainConfig:
        block = self.raw.get("main_brain", {})
        auth_env = str(block.get("auth_token_env", block.get("auth_env", "MAIN_BRAIN_AUTH_TOKEN"))).strip()
        return MainBrainConfig(
            enabled=bool(block.get("enabled", False)),
            base_url=str(block.get("base_url", "")).rstrip("/"),
            auth_header_name=str(block.get("auth_header_name", "Authorization")).strip() or "Authorization",
            auth_token=self._resolve_secret(
                {**block, "auth_token_env": auth_env},
                "auth_token",
                "MAIN_BRAIN_AUTH_TOKEN",
            ),
            owner_id=str(block.get("owner_id", "")).strip(),
            telegram_chat_id=str(block.get("telegram_chat_id", "")).strip(),
            timeout_seconds=int(block.get("timeout_seconds", 15)),
        )

    @classmethod
    def load(cls, config_path: str) -> "AgentConfig":
        path = Path(config_path).resolve()
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        config = cls(raw=raw, path=path)
        config.apply_env_files()
        return config

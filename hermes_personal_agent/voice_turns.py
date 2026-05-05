from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.parser import BytesParser
from email.policy import default
from io import BytesIO
from pathlib import Path
from typing import Any
import json
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
import webbrowser

from hermes_personal_agent.brain import BrainService
from hermes_personal_agent.companion_intents import CompanionIntentService
from hermes_personal_agent.config import VoiceRuntimeConfig
from hermes_personal_agent.main_brain import MainBrainAdapter, MainBrainError, MainBrainResult
from hermes_personal_agent.openrouter import ModelRouterAdapter
from hermes_personal_agent.orchestrator import TaskOrchestrator
from hermes_personal_agent.schemas import (
    AudioAssetRecord,
    CompanionSessionRecord,
    JobStatus,
    RemoteHandoffRecord,
    VoiceTurnRecord,
    VoiceTurnStatus,
)
from hermes_personal_agent.storage import JsonStateStore


def parse_multipart_form(content_type: str, body: bytes) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    if "multipart/form-data" not in content_type:
        raise ValueError("Expected multipart/form-data payload.")
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    fields: dict[str, str] = {}
    files: dict[str, dict[str, Any]] = {}
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename:
            files[name] = {
                "filename": filename,
                "content_type": part.get_content_type() or "application/octet-stream",
                "content": payload,
            }
        else:
            charset = part.get_content_charset("utf-8")
            fields[name] = payload.decode(charset, errors="replace")
    return fields, files


@dataclass
class AudioAssetPayload:
    path: Path
    content_type: str


@dataclass
class RoutedVoiceReply:
    reply_text: str
    linked_job_id: str = ""
    owner_id: str = ""
    remote_job_id: str = ""
    remote_status: str = ""
    remote_request_id: str = ""
    needs_followup: bool = False
    handoff_queued: bool = False


class EmotionMapper:
    POSITIVE_TOKENS = ["thank", "great", "nice", "good", "happy", "喜欢", "真好", "谢谢"]
    EXCITED_TOKENS = ["right away", "immediately", "let's", "太好了", "马上", "立刻"]
    CURIOUS_TOKENS = ["?", "what", "how", "why", "怎么", "为什么", "吗", "呢"]
    SLEEPY_TOKENS = ["wait", "later", "rest", "稍等", "等一下", "休息"]
    SAD_TOKENS = ["sorry", "failed", "error", "retry", "抱歉", "失败", "出错"]

    def map_reply(self, reply_text: str, failed: bool = False) -> str:
        text = reply_text.strip().lower()
        if failed:
            return "sad"
        if any(token in text for token in self.SAD_TOKENS):
            return "sad"
        if any(token in text for token in self.SLEEPY_TOKENS):
            return "sleepy"
        if any(token in text for token in self.EXCITED_TOKENS):
            return "excited"
        if any(token in text for token in self.POSITIVE_TOKENS):
            return "happy"
        if any(token in text for token in self.CURIOUS_TOKENS):
            return "curious"
        return "neutral"


class VoiceIntentRouter:
    CAPTURE_PREFIXES = [
        "记一下",
        "帮我记",
        "记录一下",
        "提醒我",
        "create task",
        "remember this",
        "note this",
        "add a task",
    ]
    STATUS_TOKENS = [
        "做到哪",
        "进度",
        "状态",
        "完成了吗",
        "what's the status",
        "status",
        "progress",
    ]
    APPROVE_TOKENS = ["批准", "通过", "同意", "approve", "ok that", "ship it"]
    REJECT_TOKENS = ["拒绝", "驳回", "取消那个", "reject", "deny"]

    WEB_SEARCH_TOKENS = [
        "上网搜索",
        "网页搜索",
        "打开网页",
        "打开浏览器",
        "搜一下",
        "搜索",
        "查一下",
        "google",
        "web search",
        "search web",
        "open browser",
    ]
    CODEX_EXPLICIT_TOKENS = ["codex", "code agent"]
    CODING_NOUN_TOKENS = [
        "api",
        "backend",
        "bug",
        "code",
        "codebase",
        "dashboard",
        "firmware",
        "frontend",
        "github",
        "pull request",
        "repo",
        "repository",
        "test",
        "tests",
        "代码",
        "代码库",
        "项目",
        "功能",
        "接口",
        "前端",
        "后端",
        "固件",
        "测试",
    ]
    CODING_ACTION_TOKENS = [
        "add",
        "build",
        "change",
        "debug",
        "fix",
        "implement",
        "modify",
        "refactor",
        "run",
        "wire",
        "修",
        "修复",
        "写",
        "加",
        "新增",
        "实现",
        "接入",
        "改",
        "重构",
        "跑",
        "编译",
    ]

    def classify(self, transcript: str) -> str:
        lowered = transcript.strip().lower()
        if not lowered:
            return "companion_chat"
        if any(token in lowered for token in self.WEB_SEARCH_TOKENS):
            return "open_browser_search"
        if any(token in lowered for token in self.APPROVE_TOKENS):
            return "approval_action"
        if any(token in lowered for token in self.REJECT_TOKENS):
            return "approval_action"
        if any(token in lowered for token in self.CODEX_EXPLICIT_TOKENS):
            return "codex_handoff"
        if any(lowered.startswith(token) for token in self.CAPTURE_PREFIXES):
            return "capture_task"
        if any(token in lowered for token in self.STATUS_TOKENS):
            return "status_query"
        if self._is_codex_handoff(lowered):
            return "codex_handoff"
        if any(token in lowered for token in ["待办", "任务", "todo", "task", "to-do"]):
            return "capture_task"
        return "companion_chat"

    def _is_codex_handoff(self, lowered: str) -> bool:
        if any(token in lowered for token in self.CODEX_EXPLICIT_TOKENS):
            return True
        has_coding_noun = any(token in lowered for token in self.CODING_NOUN_TOKENS)
        has_coding_action = any(token in lowered for token in self.CODING_ACTION_TOKENS)
        return has_coding_noun and has_coding_action


class SpeechGateway:
    def __init__(self, config: VoiceRuntimeConfig) -> None:
        self.config = config

    def transcribe(self, audio_bytes: bytes, filename: str = "turn.wav") -> str:
        if not self.config.api_key:
            return self._mock_transcript(audio_bytes)
        try:
            return self._transcribe_via_openai(audio_bytes, filename)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
            return self._mock_transcript(audio_bytes)

    def synthesize(self, text: str) -> tuple[bytes, str]:
        if not self.config.api_key:
            return self._mock_tts(text), "audio/wav"
        try:
            return self._tts_via_openai(text), "audio/wav"
        except (urllib.error.URLError, TimeoutError, ValueError):
            return self._mock_tts(text), "audio/wav"

    def _transcribe_via_openai(self, audio_bytes: bytes, filename: str) -> str:
        body = {
            "model": self.config.transcription_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Please transcribe this audio file into plain text. "
                                f"The spoken language is most likely {self.config.transcription_language}. "
                                "Return only the transcript with no markdown or commentary."
                            ),
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": self._base64_encode(audio_bytes),
                                "format": "wav",
                            },
                        },
                    ],
                }
            ],
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.config.api_base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://local.hermes-personal-agent",
                "X-Title": "Hermes Personal Voice Companion",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = self._extract_message_text(payload["choices"][0]["message"]["content"]).strip()
        if not text:
            raise ValueError("Empty transcription result.")
        return text

    def _tts_via_openai(self, text: str) -> bytes:
        body = json.dumps(
            {
                "model": self.config.tts_model,
                "voice": self.config.tts_device_voice,
                "input": text[:4096],
                "instructions": self.config.tts_device_instructions,
                "response_format": "pcm",
                "speed": self.config.tts_speed,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.api_base_url}/audio/speech",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            return self._pcm16_to_wav(response.read())

    def _mock_transcript(self, audio_bytes: bytes) -> str:
        duration_seconds = self._measure_duration_seconds(audio_bytes)
        if duration_seconds < 1:
            return "Hello, can you hear me?"
        if duration_seconds < 3:
            return "Hello, I want to chat."
        return f"I just spoke for about {duration_seconds:.1f} seconds and want to keep talking."

    def _mock_tts(self, text: str) -> bytes:
        sample_rate = self.config.tts_output_sample_rate
        duration = min(max(len(text) * 0.045, 0.8), 3.0)
        total_frames = int(sample_rate * duration)
        amplitude = 8000
        with BytesIO() as buffer:
            with wave.open(buffer, "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate)
                frames = bytearray()
                for index in range(total_frames):
                    progress = index / max(total_frames - 1, 1)
                    envelope = math.sin(progress * math.pi)
                    value = int(amplitude * envelope * math.sin((2 * math.pi * 440 * index) / sample_rate))
                    frames.extend(int(value).to_bytes(2, byteorder="little", signed=True))
                handle.writeframes(bytes(frames))
            return buffer.getvalue()

    def _measure_duration_seconds(self, audio_bytes: bytes) -> float:
        with wave.open(BytesIO(audio_bytes), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate() or 16000
        return frames / rate

    def _extract_message_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "".join(parts)
        return json.dumps(content, ensure_ascii=False)

    def _base64_encode(self, audio_bytes: bytes) -> str:
        import base64

        return base64.b64encode(audio_bytes).decode("ascii")

    def _pcm16_to_wav(self, pcm_bytes: bytes) -> bytes:
        with BytesIO() as buffer:
            with wave.open(buffer, "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(self.config.tts_output_sample_rate)
                handle.writeframes(pcm_bytes)
            return buffer.getvalue()


class VoiceTurnService:
    MAX_DASHBOARD_ATTACHMENTS = 4
    MAX_DASHBOARD_ATTACHMENT_BYTES = 5 * 1024 * 1024
    ALLOWED_DASHBOARD_ATTACHMENT_TYPES = {
        "application/pdf",
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/plain",
        "video/mp4",
    }

    def __init__(
        self,
        store: JsonStateStore,
        models: ModelRouterAdapter,
        orchestrator: TaskOrchestrator,
        brain: BrainService | None,
        companion_intents: CompanionIntentService | None,
        main_brain: MainBrainAdapter,
        config: VoiceRuntimeConfig,
        data_dir: Path,
    ) -> None:
        self.store = store
        self.models = models
        self.orchestrator = orchestrator
        self.brain = brain
        self.companion_intents = companion_intents
        self.main_brain = main_brain
        self.config = config
        self.speech = SpeechGateway(config)
        self.emotions = EmotionMapper()
        self.intent_router = VoiceIntentRouter()
        self.audio_dir = data_dir / "voice_cache"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._maintenance_thread.start()

    def create_turn_from_upload(
        self,
        device_id: str,
        session_id: str,
        audio_bytes: bytes,
        battery_level: float | None = None,
        filename: str = "turn.wav",
    ) -> VoiceTurnRecord:
        self.cleanup_expired_assets()
        self._validate_wav(audio_bytes)
        session = self._get_or_create_session(session_id=session_id, device_id=device_id)
        turn = VoiceTurnRecord.create(
            device_id=device_id,
            session_id=session_id,
            conversation_id=session.conversation_id,
            battery_level=battery_level,
        )
        turn.owner_id = session.owner_id
        turn.add_event("created", {"filename": filename})
        self._persist_turn(turn)

        worker = threading.Thread(
            target=self._process_turn,
            args=(turn.id, audio_bytes, filename),
            daemon=True,
        )
        worker.start()
        return turn

    def create_turn_from_text(
        self,
        device_id: str,
        session_id: str,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> VoiceTurnRecord:
        normalized_text = " ".join(str(text or "").strip().split())
        normalized_attachments = self._validate_dashboard_attachments(attachments or [])
        if not normalized_text and not normalized_attachments:
            raise ValueError("text_or_attachment_required")

        session = self._get_or_create_session(session_id=session_id, device_id=device_id)
        turn = VoiceTurnRecord.create(
            device_id=device_id,
            session_id=session_id,
            conversation_id=session.conversation_id,
            battery_level=None,
        )
        turn.owner_id = session.owner_id
        turn.attachments = normalized_attachments
        turn.add_event(
            "created",
            {
                "source": "dashboard",
                "attachment_count": len(normalized_attachments),
            },
        )
        self._persist_turn(turn)

        transcript = normalized_text or self._attachment_transcript(normalized_attachments)
        try:
            turn.intent = self.intent_router.classify(transcript)
            routed = self._route_turn(turn=turn, transcript=transcript, session=session)
            turn.transcript = transcript
            turn.reply_text = routed.reply_text
            turn.display_text = self._make_display_text(routed.reply_text)
            turn.speech_text = self._make_speech_text(routed.reply_text)
            turn.owner_id = routed.owner_id or session.owner_id
            turn.linked_job_id = routed.linked_job_id
            turn.remote_job_id = routed.remote_job_id
            turn.remote_status = routed.remote_status
            turn.remote_request_id = routed.remote_request_id
            turn.needs_followup = routed.needs_followup
            turn.handoff_queued = routed.handoff_queued
            turn.emotion = self.emotions.map_reply(routed.reply_text)
            turn.expression = "speaking"
            turn.status = VoiceTurnStatus.DONE.value
            turn.add_event(
                "completed",
                {
                    "intent": turn.intent,
                    "linked_job_id": turn.linked_job_id,
                    "remote_job_id": turn.remote_job_id,
                    "remote_status": turn.remote_status,
                    "remote_request_id": turn.remote_request_id,
                    "handoff_queued": turn.handoff_queued,
                    "source": "dashboard",
                },
            )
            self._persist_turn(turn)

            if turn.owner_id:
                session.owner_id = turn.owner_id
            if turn.remote_job_id:
                session.last_remote_job_id = turn.remote_job_id
            session.current_emotion = turn.emotion
            session.last_turn_id = turn.id
            session.append_turn(transcript, routed.reply_text, self.config.max_context_turns)
            self._persist_session(session)
        except Exception as exc:
            turn.status = VoiceTurnStatus.FAILED.value
            turn.emotion = "sad"
            turn.expression = "error"
            turn.error = str(exc)
            turn.add_event("failed", {"error": str(exc), "source": "dashboard"})
            self._persist_turn(turn)
        return turn

    def get_turn(self, turn_id: str) -> VoiceTurnRecord:
        self.cleanup_expired_assets()
        raw = self.store.get("voice_turns", turn_id)
        if raw is None:
            raise KeyError(f"Unknown voice turn: {turn_id}")
        return VoiceTurnRecord.from_dict(raw)

    def serialize_turn(self, turn: VoiceTurnRecord) -> dict[str, Any]:
        audio_url = ""
        if turn.audio_asset_id and self.store.exists("audio_assets", turn.audio_asset_id):
            audio_url = f"/api/companion/audio/{turn.audio_asset_id}"
        return {
            "turn_id": turn.id,
            "conversation_id": turn.conversation_id,
            "status": turn.status,
            "transcript": turn.transcript,
            "reply_text": turn.reply_text,
            "display_text": turn.display_text or turn.reply_text,
            "speech_text": turn.speech_text or turn.display_text or turn.reply_text,
            "emotion": turn.emotion,
            "expression": turn.expression,
            "audio_url": audio_url,
            "error": turn.error,
            "intent": turn.intent,
            "linked_job_id": turn.linked_job_id,
            "owner_id": turn.owner_id,
            "remote_job_id": turn.remote_job_id,
            "remote_status": turn.remote_status,
            "remote_request_id": turn.remote_request_id,
            "needs_followup": turn.needs_followup,
            "handoff_queued": turn.handoff_queued,
            "attachments": turn.attachments,
        }

    def get_audio_asset(self, audio_asset_id: str) -> AudioAssetPayload:
        self.cleanup_expired_assets()
        raw = self.store.get("audio_assets", audio_asset_id)
        if raw is None:
            raise KeyError(f"Unknown audio asset: {audio_asset_id}")
        asset = AudioAssetRecord.from_dict(raw)
        path = self.audio_dir / asset.filename
        if not path.exists():
            self.store.delete("audio_assets", audio_asset_id)
            raise KeyError(f"Unknown audio asset: {audio_asset_id}")
        return AudioAssetPayload(path=path, content_type=asset.content_type)

    def cleanup_expired_assets(self) -> int:
        now = datetime.now(timezone.utc)
        removed = 0
        for raw in self.store.list("audio_assets"):
            asset = AudioAssetRecord.from_dict(raw)
            expires_at = datetime.fromisoformat(asset.expires_at)
            if expires_at > now:
                continue
            path = self.audio_dir / asset.filename
            if path.exists():
                path.unlink()
            self.store.delete("audio_assets", asset.id)
            removed += 1
        return removed

    def flush_remote_handoffs(self) -> int:
        if not self.main_brain.enabled:
            return 0
        delivered = 0
        for raw in self.store.list("remote_handoffs"):
            handoff = RemoteHandoffRecord.from_dict(raw)
            if handoff.status != "pending":
                continue
            try:
                result = self.main_brain.forward_intent(
                    intent=handoff.intent,
                    transcript=handoff.transcript,
                    payload={
                        "owner_id": handoff.owner_id,
                        "telegram_chat_id": handoff.telegram_chat_id,
                        "device_id": handoff.device_id,
                        "session_id": handoff.session_id,
                        "conversation_id": handoff.conversation_id,
                        "turn_id": handoff.source_turn_id,
                        "remote_job_id": handoff.remote_job_id,
                        "metadata": handoff.metadata,
                    },
                )
                handoff.remote_job_id = result.remote_job_id or handoff.remote_job_id
                handoff.mark_attempt()
                self.store.delete("remote_handoffs", handoff.id)
                delivered += 1
            except MainBrainError as exc:
                handoff.mark_attempt(error=str(exc))
                self.store.upsert("remote_handoffs", handoff.id, handoff.to_dict())
        return delivered

    def _maintenance_loop(self) -> None:
        while True:
            try:
                self.cleanup_expired_assets()
                self.flush_remote_handoffs()
            except Exception:
                pass
            time.sleep(max(self.config.cleanup_interval_seconds, 10))

    def _process_turn(self, turn_id: str, audio_bytes: bytes, filename: str) -> None:
        turn = self.get_turn(turn_id)
        try:
            time.sleep(0.05)
            session = self._get_or_create_session(session_id=turn.session_id, device_id=turn.device_id)
            transcript = self.speech.transcribe(audio_bytes, filename=filename)
            turn.intent = self.intent_router.classify(transcript)
            routed = self._route_turn(turn=turn, transcript=transcript, session=session)

            turn.transcript = transcript
            turn.reply_text = routed.reply_text
            turn.display_text = self._make_display_text(routed.reply_text)
            turn.speech_text = self._make_speech_text(routed.reply_text)
            turn.owner_id = routed.owner_id or session.owner_id
            turn.linked_job_id = routed.linked_job_id
            turn.remote_job_id = routed.remote_job_id
            turn.remote_status = routed.remote_status
            turn.remote_request_id = routed.remote_request_id
            turn.needs_followup = routed.needs_followup
            turn.handoff_queued = routed.handoff_queued

            audio_bytes_out, audio_content_type = self.speech.synthesize(turn.speech_text)
            asset = self._store_audio(turn.id, audio_bytes_out, audio_content_type)

            turn.emotion = self.emotions.map_reply(routed.reply_text)
            turn.expression = "speaking"
            turn.audio_asset_id = asset.id
            turn.audio_content_type = audio_content_type
            turn.status = VoiceTurnStatus.DONE.value
            turn.add_event(
                "completed",
                {
                    "intent": turn.intent,
                    "linked_job_id": turn.linked_job_id,
                    "remote_job_id": turn.remote_job_id,
                    "remote_status": turn.remote_status,
                    "remote_request_id": turn.remote_request_id,
                    "handoff_queued": turn.handoff_queued,
                    "audio_asset_id": asset.id,
                },
            )
            self._persist_turn(turn)

            if turn.owner_id:
                session.owner_id = turn.owner_id
            if turn.remote_job_id:
                session.last_remote_job_id = turn.remote_job_id
            session.current_emotion = turn.emotion
            session.last_turn_id = turn.id
            session.append_turn(transcript, routed.reply_text, self.config.max_context_turns)
            self._persist_session(session)
        except Exception as exc:
            turn.status = VoiceTurnStatus.FAILED.value
            turn.emotion = "sad"
            turn.expression = "error"
            turn.error = str(exc)
            turn.add_event("failed", {"error": str(exc)})
            self._persist_turn(turn)

    def _extract_browser_search_query(self, transcript: str) -> str:
        query = transcript.strip()
        cleanup_phrases = [
            "帮我上网搜索一下",
            "帮我上网搜索",
            "上网搜索一下",
            "上网搜索",
            "网页搜索一下",
            "网页搜索",
            "帮我搜一下",
            "搜一下",
            "搜索一下",
            "搜索",
            "帮我查一下",
            "查一下",
            "打开网页看看",
            "打开网页",
            "打开浏览器",
            "用浏览器",
            "please",
            "google",
            "web search",
            "search web",
            "open browser",
            "search",
        ]
        lowered = query.lower()
        for phrase in cleanup_phrases:
            index = lowered.find(phrase)
            if index == -1:
                continue
            query = query[:index] + query[index + len(phrase):]
            lowered = query.lower()
        query = query.strip(" ，,。.!！?？:：;；")
        return query or transcript.strip()

    def _route_open_browser_search(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
    ) -> RoutedVoiceReply:
        query = self._extract_browser_search_query(transcript)
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        opened = bool(webbrowser.open(url, new=2))
        if not opened and hasattr(os, "startfile"):
            os.startfile(url)  # type: ignore[attr-defined]
            opened = True
        turn.add_event("desktop_browser_opened", {"query": query, "url": url, "opened": opened})
        if opened:
            reply = f"我已经在电脑上打开了搜索页面：{query}"
        else:
            reply = f"我试着打开电脑浏览器搜索：{query}"
        return RoutedVoiceReply(reply_text=reply, owner_id=session.owner_id)

    def _route_turn(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
    ) -> RoutedVoiceReply:
        if turn.intent == "open_browser_search":
            return self._route_open_browser_search(turn=turn, transcript=transcript, session=session)
        if turn.intent == "codex_handoff":
            if self.main_brain.enabled:
                return self._route_turn_via_main_brain(turn=turn, transcript=transcript, session=session)
            if self.companion_intents is not None:
                return self._route_turn_via_local_intents(turn=turn, transcript=transcript, session=session)
            return self._route_codex_handoff_locally(turn=turn, transcript=transcript, session=session)
        if turn.intent == "companion_chat" and self.brain is not None:
            return self._route_turn_via_local_brain(turn=turn, transcript=transcript, session=session)
        if self.main_brain.enabled and turn.intent != "companion_chat":
            return self._route_turn_via_main_brain(turn=turn, transcript=transcript, session=session)
        if turn.intent != "companion_chat" and self.companion_intents is not None:
            return self._route_turn_via_local_intents(turn=turn, transcript=transcript, session=session)
        return self._route_turn_locally(turn=turn, transcript=transcript, session=session)

    def _route_turn_locally(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
    ) -> RoutedVoiceReply:
        metadata = {
            "device_id": turn.device_id,
            "session_id": turn.session_id,
            "conversation_id": turn.conversation_id,
            "battery_level": turn.battery_level,
            "source_turn_id": turn.id,
        }

        if turn.intent == "capture_task":
            job = self.orchestrator.submit_job(
                workflow="inbox_capture",
                content=transcript,
                source_channel="companion_voice",
                metadata=metadata,
            )
            return RoutedVoiceReply(
                reply_text=f"I saved that. {self._short_job_summary(job)}",
                linked_job_id=job.id,
                owner_id=session.owner_id,
            )

        if turn.intent == "status_query":
            job = self.orchestrator.find_recent_job(device_id=turn.device_id, session_id=turn.session_id)
            if job is None:
                return RoutedVoiceReply(
                    reply_text="I could not find a recent task yet. Ask me to save one first.",
                    owner_id=session.owner_id,
                )
            return RoutedVoiceReply(
                reply_text=self._status_reply(job),
                linked_job_id=job.id,
                owner_id=session.owner_id,
            )

        if turn.intent == "approval_action":
            waiting_job = self.orchestrator.find_recent_job(
                device_id=turn.device_id,
                session_id=turn.session_id,
                statuses={JobStatus.WAITING_APPROVAL.value},
            )
            if waiting_job is None:
                return RoutedVoiceReply(
                    reply_text="I could not find a task waiting for approval.",
                    owner_id=session.owner_id,
                )
            lowered = transcript.lower()
            if any(token in lowered for token in VoiceIntentRouter.REJECT_TOKENS):
                job = self.orchestrator.reject_job(waiting_job.id, "Rejected from M5 voice companion.")
                return RoutedVoiceReply(
                    reply_text=f"Okay, I rejected it. The status is now {job.status}.",
                    linked_job_id=job.id,
                    owner_id=session.owner_id,
                )
            job = self.orchestrator.approve_job(waiting_job.id, "Approved from M5 voice companion.")
            return RoutedVoiceReply(
                reply_text=f"Okay, I approved it. The status is now {job.status}.",
                linked_job_id=job.id,
                owner_id=session.owner_id,
            )

        reply_text = self.models.generate_companion_reply(
            transcript=transcript,
            conversation_history=session.recent_turns,
            metadata=metadata,
        )
        return RoutedVoiceReply(reply_text=reply_text, owner_id=session.owner_id)

    def _route_codex_handoff_locally(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
    ) -> RoutedVoiceReply:
        job = self.orchestrator.record_handoff_job(
            workflow="codex_handoff",
            content=transcript,
            source_channel="companion_codex",
            metadata={
                "device_id": turn.device_id,
                "session_id": turn.session_id,
                "conversation_id": turn.conversation_id,
                "battery_level": turn.battery_level,
                "source_turn_id": turn.id,
                "delegate_to": "codex",
                "codex_reasoning": "high",
                "spec_kit_required": True,
                "skip_flash_planning": True,
            },
            summary="Coding request queued for Codex high-reasoning execution.",
        )
        return RoutedVoiceReply(
            reply_text="已自动交给 Codex。这个会走高推理编码流程，不用 Flash 做架构规划。",
            linked_job_id=job.id,
            owner_id=session.owner_id,
            needs_followup=True,
        )

    def _route_turn_via_local_brain(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
    ) -> RoutedVoiceReply:
        assert self.brain is not None
        reply_text = self.brain.generate_companion_chat_reply(
            transcript=transcript,
            owner_id=session.owner_id,
            device_id=turn.device_id,
            session_id=turn.session_id,
            battery_level=turn.battery_level,
        )
        return RoutedVoiceReply(reply_text=reply_text, owner_id=session.owner_id or self.main_brain.config.owner_id)

    def _route_turn_via_local_intents(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
    ) -> RoutedVoiceReply:
        assert self.companion_intents is not None
        payload = self._build_main_brain_payload(turn=turn, session=session)
        result = self.companion_intents.handle_intent(
            {
                **payload,
                "intent": turn.intent,
                "transcript": transcript,
            }
        )
        turn.add_event(
            "local_brain_forwarded",
            {
                "intent": turn.intent,
                "remote_job_id": result.get("remote_job_id", ""),
                "remote_status": result.get("status", ""),
                "delivery_result": "delivered",
            },
        )
        return self._routed_reply_from_main_brain(
            result=MainBrainResult.from_dict(
                {
                    "ok": result.get("ok", True),
                    "owner_id": result.get("owner_id", payload.get("owner_id", "")),
                    "remote_job_id": result.get("remote_job_id", ""),
                    "status": result.get("status", ""),
                    "short_reply": result.get("short_reply", result.get("reply_text", "")),
                    "long_reply_text": result.get("long_reply_text", ""),
                    "long_reply_url": result.get("long_reply_url", ""),
                    "needs_followup": result.get("needs_followup", False),
                    "remote_request_id": result.get("remote_request_id", payload.get("turn_id", "")),
                }
            ),
            session=session,
        )

    def _route_turn_via_main_brain(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
    ) -> RoutedVoiceReply:
        payload = self._build_main_brain_payload(turn=turn, session=session)
        try:
            result = self.main_brain.forward_intent(intent=turn.intent, transcript=transcript, payload=payload)
            turn.add_event(
                "main_brain_forwarded",
                {
                    "intent": turn.intent,
                    "remote_request_id": result.remote_request_id,
                    "remote_job_id": result.remote_job_id,
                    "remote_status": result.status,
                    "delivery_result": "delivered",
                },
            )
        except MainBrainError as exc:
            turn.add_event(
                "main_brain_forward_failed",
                {
                    "intent": turn.intent,
                    "delivery_result": "failed",
                    "fallback_reason": str(exc),
                },
            )
            return self._handle_main_brain_error(turn=turn, transcript=transcript, session=session, error=str(exc))
        return self._routed_reply_from_main_brain(result=result, session=session)

    def _build_main_brain_payload(
        self,
        *,
        turn: VoiceTurnRecord,
        session: CompanionSessionRecord,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {"source": "m5_companion", "source_turn_id": turn.id}
        if turn.intent == "codex_handoff":
            metadata.update(
                {
                    "delegate_to": "codex",
                    "codex_reasoning": "high",
                    "spec_kit_required": True,
                    "skip_flash_planning": True,
                }
            )
        return {
            "owner_id": session.owner_id or self.main_brain.config.owner_id,
            "telegram_chat_id": session.telegram_chat_id or self.main_brain.config.telegram_chat_id,
            "device_id": turn.device_id,
            "session_id": turn.session_id,
            "conversation_id": turn.conversation_id,
            "battery_level": turn.battery_level,
            "turn_id": turn.id,
            "remote_job_id": session.last_remote_job_id,
            "metadata": metadata,
        }

    def _routed_reply_from_main_brain(
        self,
        *,
        result: MainBrainResult,
        session: CompanionSessionRecord,
    ) -> RoutedVoiceReply:
        reply_text = result.short_reply.strip() or self._summarize_remote_result(result)
        if result.needs_followup:
            reply_text = f"{reply_text} Check Telegram for the full details."
        return RoutedVoiceReply(
            reply_text=reply_text,
            linked_job_id=result.remote_job_id,
            owner_id=result.owner_id or session.owner_id or self.main_brain.config.owner_id,
            remote_job_id=result.remote_job_id,
            remote_status=result.status,
            remote_request_id=result.remote_request_id,
            needs_followup=result.needs_followup,
        )

    def _handle_main_brain_error(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
        error: str,
    ) -> RoutedVoiceReply:
        if turn.intent in {"capture_task", "codex_handoff"}:
            handoff = self._queue_remote_handoff(turn=turn, transcript=transcript, session=session, error=error)
            if turn.intent == "codex_handoff":
                return RoutedVoiceReply(
                    reply_text="我已经把这个 Codex 编码请求先缓存了，主脑恢复后会继续同步。",
                    owner_id=handoff.owner_id,
                    remote_job_id=handoff.remote_job_id,
                    handoff_queued=True,
                )
            return RoutedVoiceReply(
                reply_text="I saved that and will sync it to Telegram when the main brain is back.",
                owner_id=handoff.owner_id,
                remote_job_id=handoff.remote_job_id,
                handoff_queued=True,
            )
        if turn.intent == "status_query":
            return RoutedVoiceReply(
                reply_text="I cannot reach the main brain right now, so I do not have the latest Telegram status.",
                owner_id=session.owner_id,
            )
        if turn.intent == "approval_action":
            return RoutedVoiceReply(
                reply_text="I could not reach the main brain, so I have not approved or rejected anything yet.",
                owner_id=session.owner_id,
            )
        return RoutedVoiceReply(reply_text="I could not sync that with the main brain right now.", owner_id=session.owner_id)

    def _queue_remote_handoff(
        self,
        *,
        turn: VoiceTurnRecord,
        transcript: str,
        session: CompanionSessionRecord,
        error: str,
    ) -> RemoteHandoffRecord:
        metadata: dict[str, Any] = {"battery_level": turn.battery_level}
        if turn.intent == "codex_handoff":
            metadata.update(
                {
                    "delegate_to": "codex",
                    "codex_reasoning": "high",
                    "spec_kit_required": True,
                    "skip_flash_planning": True,
                }
            )
        handoff = RemoteHandoffRecord.create(
            intent=turn.intent,
            transcript=transcript,
            owner_id=session.owner_id or self.main_brain.config.owner_id,
            telegram_chat_id=session.telegram_chat_id or self.main_brain.config.telegram_chat_id,
            device_id=turn.device_id,
            session_id=turn.session_id,
            conversation_id=turn.conversation_id,
            source_turn_id=turn.id,
            remote_job_id=session.last_remote_job_id,
            metadata=metadata,
        )
        handoff.mark_attempt(error=error)
        self.store.upsert("remote_handoffs", handoff.id, handoff.to_dict())
        return handoff

    def _get_or_create_session(self, session_id: str, device_id: str) -> CompanionSessionRecord:
        raw = self.store.get("companion_sessions", session_id)
        if raw is not None:
            session = CompanionSessionRecord.from_dict(raw)
            session.device_id = device_id
            if not session.owner_id:
                session.owner_id = self.main_brain.config.owner_id
            if not session.telegram_chat_id:
                session.telegram_chat_id = self.main_brain.config.telegram_chat_id
            session.updated_at = datetime.now(timezone.utc).isoformat()
            self._persist_session(session)
            return session
        session = CompanionSessionRecord.create(session_id=session_id, device_id=device_id)
        session.owner_id = self.main_brain.config.owner_id
        session.telegram_chat_id = self.main_brain.config.telegram_chat_id
        self._persist_session(session)
        return session

    def _persist_turn(self, turn: VoiceTurnRecord) -> None:
        self.store.upsert("voice_turns", turn.id, turn.to_dict())

    def _persist_session(self, session: CompanionSessionRecord) -> None:
        self.store.upsert("companion_sessions", session.session_id, session.to_dict())

    def _validate_dashboard_attachments(self, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(attachments) > self.MAX_DASHBOARD_ATTACHMENTS:
            raise ValueError("too_many_attachments")

        normalized: list[dict[str, Any]] = []
        for index, attachment in enumerate(attachments):
            filename = os.path.basename(str(attachment.get("filename") or "")).strip()
            content_type = str(attachment.get("content_type") or "application/octet-stream").strip().lower()
            try:
                size_bytes = int(attachment.get("size_bytes") or 0)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid_attachment_size") from exc

            if not filename:
                raise ValueError("attachment_filename_required")
            if content_type not in self.ALLOWED_DASHBOARD_ATTACHMENT_TYPES:
                raise ValueError(f"unsupported_attachment_type:{content_type}")
            if size_bytes <= 0:
                raise ValueError("invalid_attachment_size")
            if size_bytes > self.MAX_DASHBOARD_ATTACHMENT_BYTES:
                raise ValueError("attachment_too_large")

            normalized.append(
                {
                    "id": f"att_{int(time.time() * 1000)}_{index}",
                    "filename": filename[:160],
                    "content_type": content_type,
                    "size_bytes": size_bytes,
                    "status": "accepted",
                    "storage_ref": "",
                }
            )
        return normalized

    def _attachment_transcript(self, attachments: list[dict[str, Any]]) -> str:
        names = ", ".join(attachment["filename"] for attachment in attachments)
        return f"Dashboard shared attachments: {names}"

    def _store_audio(self, turn_id: str, audio_bytes: bytes, content_type: str) -> AudioAssetRecord:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=self.config.audio_ttl_seconds)).isoformat()
        asset = AudioAssetRecord.create(
            turn_id=turn_id,
            filename=f"{turn_id}.wav",
            content_type=content_type,
            expires_at=expires_at,
        )
        path = self.audio_dir / asset.filename
        path.write_bytes(audio_bytes)
        self.store.upsert("audio_assets", asset.id, asset.to_dict())
        return asset

    def _validate_wav(self, audio_bytes: bytes) -> None:
        try:
            with wave.open(BytesIO(audio_bytes), "rb") as handle:
                channels = handle.getnchannels()
                sample_width = handle.getsampwidth()
                sample_rate = handle.getframerate()
                compression = handle.getcomptype()
        except wave.Error as exc:
            raise ValueError("Invalid WAV payload.") from exc
        if channels != 1:
            raise ValueError("Voice turn audio must be mono.")
        if sample_width != 2:
            raise ValueError("Voice turn audio must be 16-bit PCM.")
        if sample_rate != 16000:
            raise ValueError("Voice turn audio must be 16kHz.")
        if compression != "NONE":
            raise ValueError("Voice turn audio must be PCM.")

    def _make_display_text(self, text: str) -> str:
        compact = " ".join(text.strip().split())
        if len(compact) <= 42:
            return compact
        return compact[:39].rstrip() + "..."

    def _make_speech_text(self, text: str) -> str:
        compact = " ".join(text.strip().split())
        compact = self._first_sentence(compact)
        if len(compact) <= 14:
            return compact
        short = compact[:14].rstrip(" .,!?;:，。！？；：、")
        if not short:
            short = compact[:14]
        if short[-1:] not in {".", "!", "?", "。", "！", "？"}:
            short += "。"
        return short

    def _first_sentence(self, text: str) -> str:
        stripped = text.strip()
        if not stripped:
            return ""
        for index, char in enumerate(stripped):
            if char in {".", "!", "?", "。", "！", "？"}:
                return stripped[: index + 1].strip()
        return stripped

    def _summarize_remote_result(self, result: MainBrainResult) -> str:
        for value in (result.long_reply_text, result.long_reply_url, result.status):
            if value.strip():
                return self._make_display_text(value)
        return "The main brain handled it."

    def _short_job_summary(self, job) -> str:
        summary = ""
        if job.result:
            summary = str(job.result.get("summary", "")).strip()
        if summary:
            return f"Job {job.id} is {job.status}. {self._make_display_text(summary)}"
        return f"Job {job.id} is {job.status}."

    def _status_reply(self, job) -> str:
        summary = ""
        if job.result:
            summary = str(job.result.get("summary", "")).strip()
        if summary:
            return f"Your latest task {job.id} is {job.status}. {self._make_display_text(summary)}"
        return f"Your latest task {job.id} is {job.status}."

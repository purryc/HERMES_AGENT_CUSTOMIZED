from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class JobStatus(str, Enum):
    NEW = "new"
    PLANNED = "planned"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"


class WorkflowName(str, Enum):
    INBOX_CAPTURE = "inbox_capture"
    DRAFTING_ASSISTANT = "drafting_assistant"
    KNOWLEDGE_DISTILL = "knowledge_distill"


@dataclass
class WorkflowResult:
    summary: str
    actions: list[str]
    open_questions: list[str]
    confidence: float
    needs_approval: bool
    structured_payload: dict[str, Any] = field(default_factory=dict)
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WorkflowResult":
        return cls(**value)


@dataclass
class JobRecord:
    id: str
    workflow: str
    status: str
    content: str
    source_channel: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    result: dict[str, Any] | None = None
    memory_candidate_ids: list[str] = field(default_factory=list)
    event_log: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        workflow: str,
        content: str,
        source_channel: str,
        metadata: dict[str, Any] | None = None,
    ) -> "JobRecord":
        now = utc_now()
        return cls(
            id=new_id("job"),
            workflow=workflow,
            status=JobStatus.NEW.value,
            content=content,
            source_channel=source_channel,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

    def add_event(self, event: str, payload: dict[str, Any] | None = None) -> None:
        self.event_log.append(
            {
                "timestamp": utc_now(),
                "event": event,
                "payload": payload or {},
            }
        )
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "JobRecord":
        return cls(**value)


@dataclass
class MemoryCandidate:
    id: str
    job_id: str
    content: str
    category: str
    status: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        job_id: str,
        content: str,
        category: str = "preference_or_pattern",
        metadata: dict[str, Any] | None = None,
    ) -> "MemoryCandidate":
        now = utc_now()
        return cls(
            id=new_id("memcand"),
            job_id=job_id,
            content=content,
            category=category,
            status="candidate",
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MemoryCandidate":
        return cls(**value)


@dataclass
class MemoryRecord:
    id: str
    content: str
    category: str
    source_candidate_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        content: str,
        category: str,
        source_candidate_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> "MemoryRecord":
        now = utc_now()
        return cls(
            id=new_id("memory"),
            content=content,
            category=category,
            source_candidate_id=source_candidate_id,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MemoryRecord":
        return cls(**value)


@dataclass
class SkillTemplate:
    name: str
    workflow: str
    description: str
    version: str
    active: bool
    phase: str
    output_schema: list[str]
    usage_count: int = 0
    success_count: int = 0
    last_used_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SkillTemplate":
        return cls(**value)


@dataclass
class DeviceEvent:
    id: str
    device_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str

    @classmethod
    def create(cls, device_id: str, event_type: str, payload: dict[str, Any]) -> "DeviceEvent":
        return cls(
            id=new_id("device"),
            device_id=device_id,
            event_type=event_type,
            payload=payload,
            created_at=utc_now(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VoiceTurnStatus(str, Enum):
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class VoiceTurnRecord:
    id: str
    device_id: str
    session_id: str
    conversation_id: str
    status: str
    transcript: str
    reply_text: str
    display_text: str
    emotion: str
    expression: str
    created_at: str
    updated_at: str
    speech_text: str = ""
    audio_asset_id: str = ""
    audio_content_type: str = ""
    battery_level: float | None = None
    error: str = ""
    intent: str = "companion_chat"
    linked_job_id: str = ""
    owner_id: str = ""
    remote_job_id: str = ""
    remote_status: str = ""
    remote_request_id: str = ""
    needs_followup: bool = False
    handoff_queued: bool = False
    attachments: list[dict[str, Any]] = field(default_factory=list)
    event_log: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        device_id: str,
        session_id: str,
        conversation_id: str,
        battery_level: float | None = None,
    ) -> "VoiceTurnRecord":
        now = utc_now()
        return cls(
            id=new_id("turn"),
            device_id=device_id,
            session_id=session_id,
            conversation_id=conversation_id,
            status=VoiceTurnStatus.PROCESSING.value,
            transcript="",
            reply_text="",
            display_text="",
            emotion="neutral",
            expression="thinking",
            created_at=now,
            updated_at=now,
            speech_text="",
            battery_level=battery_level,
        )

    def add_event(self, event: str, payload: dict[str, Any] | None = None) -> None:
        self.event_log.append(
            {
                "timestamp": utc_now(),
                "event": event,
                "payload": payload or {},
            }
        )
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "VoiceTurnRecord":
        return cls(**value)


@dataclass
class CompanionSessionRecord:
    session_id: str
    device_id: str
    conversation_id: str
    created_at: str
    updated_at: str
    current_emotion: str = "neutral"
    last_turn_id: str = ""
    owner_id: str = ""
    telegram_chat_id: str = ""
    last_remote_job_id: str = ""
    recent_turns: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def create(cls, session_id: str, device_id: str) -> "CompanionSessionRecord":
        now = utc_now()
        return cls(
            session_id=session_id,
            device_id=device_id,
            conversation_id=new_id("conv"),
            created_at=now,
            updated_at=now,
        )

    def append_turn(self, transcript: str, reply_text: str, max_turns: int) -> None:
        self.recent_turns.append({"role": "user", "content": transcript})
        self.recent_turns.append({"role": "assistant", "content": reply_text})
        if len(self.recent_turns) > max_turns * 2:
            self.recent_turns = self.recent_turns[-max_turns * 2 :]
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CompanionSessionRecord":
        return cls(**value)


@dataclass
class AudioAssetRecord:
    id: str
    turn_id: str
    filename: str
    content_type: str
    created_at: str
    expires_at: str

    @classmethod
    def create(
        cls,
        turn_id: str,
        filename: str,
        content_type: str,
        expires_at: str,
    ) -> "AudioAssetRecord":
        return cls(
            id=new_id("audio"),
            turn_id=turn_id,
            filename=filename,
            content_type=content_type,
            created_at=utc_now(),
            expires_at=expires_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AudioAssetRecord":
        return cls(**value)


@dataclass
class RemoteHandoffRecord:
    id: str
    intent: str
    transcript: str
    owner_id: str
    telegram_chat_id: str
    device_id: str
    session_id: str
    conversation_id: str
    source_turn_id: str
    remote_job_id: str
    attempts: int
    status: str
    last_error: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        intent: str,
        transcript: str,
        owner_id: str,
        telegram_chat_id: str,
        device_id: str,
        session_id: str,
        conversation_id: str,
        source_turn_id: str,
        remote_job_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "RemoteHandoffRecord":
        now = utc_now()
        return cls(
            id=new_id("handoff"),
            intent=intent,
            transcript=transcript,
            owner_id=owner_id,
            telegram_chat_id=telegram_chat_id,
            device_id=device_id,
            session_id=session_id,
            conversation_id=conversation_id,
            source_turn_id=source_turn_id,
            remote_job_id=remote_job_id,
            attempts=0,
            status="pending",
            last_error="",
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

    def mark_attempt(self, error: str = "") -> None:
        self.attempts += 1
        self.last_error = error
        self.updated_at = utc_now()
        self.status = "pending" if error else "delivered"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RemoteHandoffRecord":
        return cls(**value)


@dataclass
class ConversationRecord:
    id: str
    owner_id: str
    channel: str
    thread_key: str
    created_at: str
    updated_at: str
    surface: str = ""
    telegram_chat_id: str = ""
    device_id: str = ""
    session_id: str = ""
    recent_turns: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        owner_id: str,
        channel: str,
        thread_key: str,
        surface: str = "",
        telegram_chat_id: str = "",
        device_id: str = "",
        session_id: str = "",
    ) -> "ConversationRecord":
        now = utc_now()
        return cls(
            id=new_id("chat"),
            owner_id=owner_id,
            channel=channel,
            thread_key=thread_key,
            created_at=now,
            updated_at=now,
            surface=surface,
            telegram_chat_id=telegram_chat_id,
            device_id=device_id,
            session_id=session_id,
        )

    def append_turn(self, user_text: str, assistant_text: str, max_turns: int) -> None:
        self.recent_turns.append({"role": "user", "content": user_text})
        self.recent_turns.append({"role": "assistant", "content": assistant_text})
        if len(self.recent_turns) > max_turns * 2:
            self.recent_turns = self.recent_turns[-max_turns * 2 :]
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConversationRecord":
        return cls(**value)

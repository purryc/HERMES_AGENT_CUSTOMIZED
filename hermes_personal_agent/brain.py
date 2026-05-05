from __future__ import annotations

from hermes_personal_agent.memory import MemoryManager
from hermes_personal_agent.openrouter import ModelRouterAdapter
from hermes_personal_agent.orchestrator import TaskOrchestrator
from hermes_personal_agent.schemas import ConversationRecord, MemoryRecord


class BrainService:
    def __init__(
        self,
        *,
        store,
        models: ModelRouterAdapter,
        orchestrator: TaskOrchestrator,
        memory: MemoryManager,
        default_owner_id: str = "local_owner",
    ) -> None:
        self.store = store
        self.models = models
        self.orchestrator = orchestrator
        self.memory = memory
        self.default_owner_id = default_owner_id or "local_owner"

    def handle_telegram_message(self, payload: dict) -> dict:
        message_id = str(payload.get("message_id") or payload.get("id") or "").strip()
        request_id = f"telegram:{message_id}" if message_id else ""
        if request_id and self.store.exists("messages", request_id):
            saved = self.store.get("messages", request_id)
            if saved is not None:
                return dict(saved["reply_payload"])

        text = str(payload.get("text", "")).strip()
        sender = str(payload.get("sender", "unknown")).strip() or "unknown"
        telegram_chat_id = str(
            payload.get("telegram_chat_id")
            or payload.get("chat_id")
            or payload.get("chat", {}).get("id", "")
        ).strip()
        owner_id = self._resolve_owner_id(
            explicit_owner=str(payload.get("owner_id", "")).strip(),
            telegram_chat_id=telegram_chat_id,
            fallback=sender,
        )

        if not text:
            response = {
                "ok": True,
                "deduplicated": False,
                "mode": "ignored",
                "conversation_id": "",
                "reply_text": "Empty Telegram message ignored.",
                "long_reply_text": "",
                "job_id": None,
            }
            self._store_message(request_id=request_id, payload=payload, response=response)
            return response

        lowered = text.lower()
        if lowered.startswith("/status") or lowered.startswith("status "):
            response = self._status_response(text=text, owner_id=owner_id, telegram_chat_id=telegram_chat_id)
        elif lowered.startswith("/approve") or lowered.startswith("approve "):
            response = self._approval_response(text=text, approve=True)
        elif lowered.startswith("/reject") or lowered.startswith("reject "):
            response = self._approval_response(text=text, approve=False)
        elif lowered.startswith("/jobs"):
            response = self._jobs_response(owner_id=owner_id, telegram_chat_id=telegram_chat_id)
        elif lowered.startswith("draft:") or lowered.startswith("distill:") or lowered.startswith("task:"):
            response = self._task_response(
                text=text,
                owner_id=owner_id,
                telegram_chat_id=telegram_chat_id,
                sender=sender,
            )
        else:
            response = self._conversation_response(
                text=text,
                owner_id=owner_id,
                telegram_chat_id=telegram_chat_id,
                sender=sender,
            )

        self._store_message(request_id=request_id, payload=payload, response=response)
        return response

    def generate_companion_chat_reply(
        self,
        *,
        transcript: str,
        owner_id: str,
        device_id: str,
        session_id: str,
        battery_level: float | None,
    ) -> str:
        owner_id = self._resolve_owner_id(explicit_owner=owner_id, telegram_chat_id="", fallback=device_id)
        thread_key = f"m5:{owner_id}:{session_id or device_id}"
        conversation = self._get_or_create_conversation(
            owner_id=owner_id,
            channel="m5",
            thread_key=thread_key,
            surface="m5_companion",
            device_id=device_id,
            session_id=session_id,
        )
        context = self._build_owner_context(owner_id=owner_id, telegram_chat_id="")
        reply = self.models.generate_brain_reply(
            channel="m5",
            user_text=transcript,
            conversation_history=conversation.recent_turns,
            context=context | {"device_id": device_id, "session_id": session_id, "battery_level": battery_level},
        )
        conversation.append_turn(transcript, reply, max_turns=6)
        self.store.upsert("conversations", conversation.id, conversation.to_dict())
        return reply

    def _conversation_response(
        self,
        *,
        text: str,
        owner_id: str,
        telegram_chat_id: str,
        sender: str,
    ) -> dict:
        thread_key = f"telegram:{telegram_chat_id or sender or owner_id}"
        conversation = self._get_or_create_conversation(
            owner_id=owner_id,
            channel="telegram",
            thread_key=thread_key,
            surface="telegram",
            telegram_chat_id=telegram_chat_id,
        )
        context = self._build_owner_context(owner_id=owner_id, telegram_chat_id=telegram_chat_id)
        reply = self.models.generate_brain_reply(
            channel="telegram",
            user_text=text,
            conversation_history=conversation.recent_turns,
            context=context,
        )
        conversation.append_turn(text, reply, max_turns=12)
        self.store.upsert("conversations", conversation.id, conversation.to_dict())
        return {
            "ok": True,
            "deduplicated": False,
            "mode": "conversation",
            "conversation_id": conversation.id,
            "reply_text": reply,
            "long_reply_text": reply,
            "job_id": None,
        }

    def _task_response(
        self,
        *,
        text: str,
        owner_id: str,
        telegram_chat_id: str,
        sender: str,
    ) -> dict:
        lowered = text.lower()
        workflow = "inbox_capture"
        content = text
        if lowered.startswith("draft:"):
            workflow = "drafting_assistant"
            content = text.split(":", 1)[1].strip()
        elif lowered.startswith("distill:"):
            workflow = "knowledge_distill"
            content = text.split(":", 1)[1].strip()
        elif lowered.startswith("task:"):
            content = text.split(":", 1)[1].strip()

        job = self.orchestrator.submit_job(
            workflow=workflow,
            content=content,
            source_channel="telegram",
            metadata={
                "owner_id": owner_id,
                "telegram_chat_id": telegram_chat_id,
                "sender": sender,
                "channel": "telegram",
            },
        )
        return {
            "ok": True,
            "deduplicated": False,
            "mode": "task",
            "conversation_id": "",
            "reply_text": self._telegram_job_reply(job),
            "long_reply_text": self.orchestrator.format_status(job),
            "job_id": job.id,
        }

    def _status_response(self, *, text: str, owner_id: str, telegram_chat_id: str) -> dict:
        parts = text.replace("/status", "status", 1).split(maxsplit=1)
        job = None
        if len(parts) > 1 and parts[1].strip():
            try:
                job = self.orchestrator.get_job(parts[1].strip())
            except KeyError:
                job = None
        if job is None:
            job = self._find_owner_job(owner_id=owner_id, telegram_chat_id=telegram_chat_id)
        if job is None:
            return {
                "ok": True,
                "deduplicated": False,
                "mode": "status",
                "conversation_id": "",
                "reply_text": "I could not find a recent task yet.",
                "long_reply_text": "",
                "job_id": None,
            }
        return {
            "ok": True,
            "deduplicated": False,
            "mode": "status",
            "conversation_id": "",
            "reply_text": self._telegram_job_reply(job),
            "long_reply_text": self.orchestrator.format_status(job),
            "job_id": job.id,
        }

    def _approval_response(self, *, text: str, approve: bool) -> dict:
        normalized = text.replace("/approve", "approve", 1).replace("/reject", "reject", 1)
        parts = normalized.split(maxsplit=2)
        if len(parts) < 2:
            raise ValueError("Approval commands require a job id.")
        job_id = parts[1].strip()
        comment = parts[2].strip() if len(parts) > 2 else ""
        job = self.orchestrator.approve_job(job_id, comment) if approve else self.orchestrator.reject_job(job_id, comment)
        verb = "Approved" if approve else "Rejected"
        return {
            "ok": True,
            "deduplicated": False,
            "mode": "approval",
            "conversation_id": "",
            "reply_text": f"{verb} {job.id}. Current status: {job.status}",
            "long_reply_text": self.orchestrator.format_status(job),
            "job_id": job.id,
        }

    def _jobs_response(self, *, owner_id: str, telegram_chat_id: str) -> dict:
        jobs = self._find_owner_jobs(owner_id=owner_id, telegram_chat_id=telegram_chat_id)[:5]
        if not jobs:
            return {
                "ok": True,
                "deduplicated": False,
                "mode": "jobs",
                "conversation_id": "",
                "reply_text": "No recent jobs yet.",
                "long_reply_text": "",
                "job_id": None,
            }
        lines = [f"{job.id} {job.status} {job.workflow}" for job in jobs]
        return {
            "ok": True,
            "deduplicated": False,
            "mode": "jobs",
            "conversation_id": "",
            "reply_text": f"{len(jobs)} recent jobs ready.",
            "long_reply_text": "\n".join(lines),
            "job_id": jobs[0].id,
        }

    def _get_or_create_conversation(
        self,
        *,
        owner_id: str,
        channel: str,
        thread_key: str,
        surface: str,
        telegram_chat_id: str = "",
        device_id: str = "",
        session_id: str = "",
    ) -> ConversationRecord:
        for raw in self.store.list("conversations"):
            conversation = ConversationRecord.from_dict(raw)
            if conversation.channel == channel and conversation.thread_key == thread_key:
                return conversation
        conversation = ConversationRecord.create(
            owner_id=owner_id,
            channel=channel,
            thread_key=thread_key,
            surface=surface,
            telegram_chat_id=telegram_chat_id,
            device_id=device_id,
            session_id=session_id,
        )
        self.store.upsert("conversations", conversation.id, conversation.to_dict())
        return conversation

    def _build_owner_context(self, *, owner_id: str, telegram_chat_id: str) -> dict:
        memories = []
        for raw in self.store.list("memories")[-5:]:
            memory = MemoryRecord.from_dict(raw)
            memories.append(memory.content)
        jobs = self._find_owner_jobs(owner_id=owner_id, telegram_chat_id=telegram_chat_id)[:3]
        job_summaries = []
        for job in jobs:
            summary = ""
            if job.result:
                summary = str(job.result.get("summary", "")).strip()
            job_summaries.append(
                {
                    "job_id": job.id,
                    "status": job.status,
                    "workflow": job.workflow,
                    "summary": summary,
                }
            )
        return {
            "owner_id": owner_id,
            "memories": memories,
            "recent_jobs": job_summaries,
            "persona": "Hermes CEO Agent",
        }

    def _find_owner_jobs(self, *, owner_id: str, telegram_chat_id: str):
        jobs = []
        for job in self.orchestrator.list_jobs():
            metadata = job.metadata or {}
            if owner_id and metadata.get("owner_id") == owner_id:
                jobs.append(job)
                continue
            if telegram_chat_id and metadata.get("telegram_chat_id") == telegram_chat_id:
                jobs.append(job)
        if jobs:
            return jobs
        return self.orchestrator.list_jobs()

    def _find_owner_job(self, *, owner_id: str, telegram_chat_id: str):
        jobs = self._find_owner_jobs(owner_id=owner_id, telegram_chat_id=telegram_chat_id)
        return jobs[0] if jobs else None

    def _resolve_owner_id(self, *, explicit_owner: str, telegram_chat_id: str, fallback: str) -> str:
        return explicit_owner or telegram_chat_id or fallback or self.default_owner_id

    def _telegram_job_reply(self, job) -> str:
        summary = ""
        if job.result:
            summary = str(job.result.get("summary", "")).strip()
        if summary:
            return f"{job.id} is {job.status}. {summary}"
        return f"{job.id} is {job.status}."

    def _store_message(self, *, request_id: str, payload: dict, response: dict) -> None:
        if not request_id:
            return
        self.store.upsert(
            "messages",
            request_id,
            {
                "id": request_id,
                "channel": "telegram",
                "sender": payload.get("sender", "unknown"),
                "payload": payload,
                "reply": response.get("reply_text", ""),
                "job_id": response.get("job_id"),
                "reply_payload": response,
            },
        )

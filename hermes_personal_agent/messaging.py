from __future__ import annotations

from hermes_personal_agent.orchestrator import TaskOrchestrator
from hermes_personal_agent.storage import JsonStateStore


class MessagingGateway:
    def __init__(self, store: JsonStateStore, orchestrator: TaskOrchestrator) -> None:
        self.store = store
        self.orchestrator = orchestrator

    def ingest(self, channel: str, payload: dict) -> dict:
        message_id = payload.get("message_id") or payload.get("id")
        if message_id and self.store.exists("messages", message_id):
            saved = self.store.get("messages", message_id)
            return {
                "deduplicated": True,
                "reply": saved.get("reply", "Duplicate message ignored."),
                "job_id": saved.get("job_id"),
            }

        text = str(payload.get("text", "")).strip()
        sender = payload.get("sender", "unknown")

        if not text:
            reply = "Empty message ignored."
            self._store_message(message_id, channel, sender, payload, reply, None)
            return {"deduplicated": False, "reply": reply, "job_id": None}

        lowered = text.lower()
        if lowered.startswith("status "):
            job_id = text.split(maxsplit=1)[1].strip()
            job = self.orchestrator.get_job(job_id)
            reply = self.orchestrator.format_status(job)
            self._store_message(message_id, channel, sender, payload, reply, job.id)
            return {"deduplicated": False, "reply": reply, "job_id": job.id}

        if lowered.startswith("approve "):
            parts = text.split(maxsplit=2)
            job_id = parts[1]
            comment = parts[2] if len(parts) > 2 else ""
            job = self.orchestrator.approve_job(job_id, comment)
            reply = f"Approved {job.id}. Current status: {job.status}"
            self._store_message(message_id, channel, sender, payload, reply, job.id)
            return {"deduplicated": False, "reply": reply, "job_id": job.id}

        if lowered.startswith("reject "):
            parts = text.split(maxsplit=2)
            job_id = parts[1]
            reason = parts[2] if len(parts) > 2 else ""
            job = self.orchestrator.reject_job(job_id, reason)
            reply = f"Rejected {job.id}. Current status: {job.status}"
            self._store_message(message_id, channel, sender, payload, reply, job.id)
            return {"deduplicated": False, "reply": reply, "job_id": job.id}

        workflow = "inbox_capture"
        content = text
        if lowered.startswith("draft:"):
            workflow = "drafting_assistant"
            content = text.split(":", 1)[1].strip()
        elif lowered.startswith("distill:"):
            workflow = "knowledge_distill"
            content = text.split(":", 1)[1].strip()

        metadata = dict(payload.get("metadata", {}))
        metadata["sender"] = sender
        metadata["channel"] = channel
        if payload.get("attachments"):
            metadata["attachments"] = payload["attachments"]
            metadata["has_image"] = True

        job = self.orchestrator.submit_job(
            workflow=workflow,
            content=content,
            source_channel=channel,
            metadata=metadata,
        )
        reply = self.orchestrator.format_status(job)
        self._store_message(message_id, channel, sender, payload, reply, job.id)
        return {"deduplicated": False, "reply": reply, "job_id": job.id}

    def _store_message(
        self,
        message_id: str | None,
        channel: str,
        sender: str,
        payload: dict,
        reply: str,
        job_id: str | None,
    ) -> None:
        if not message_id:
            return
        record = {
            "id": message_id,
            "channel": channel,
            "sender": sender,
            "payload": payload,
            "reply": reply,
            "job_id": job_id,
        }
        self.store.upsert("messages", message_id, record)


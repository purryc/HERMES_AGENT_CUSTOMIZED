from __future__ import annotations

from hermes_personal_agent.orchestrator import TaskOrchestrator


class CompanionIntentService:
    APPROVE_TOKENS = ("批准", "通过", "同意", "approve", "ship it", "ok that")
    REJECT_TOKENS = ("拒绝", "驳回", "取消", "reject", "deny")

    def __init__(self, store, orchestrator: TaskOrchestrator) -> None:
        self.store = store
        self.orchestrator = orchestrator

    def handle_intent(self, payload: dict) -> dict:
        turn_id = str(payload.get("turn_id", "")).strip()
        request_id = self._request_id(turn_id)
        if request_id and self.store.exists("messages", request_id):
            saved = self.store.get("messages", request_id)
            if saved is not None:
                return dict(saved["reply_payload"])

        intent = str(payload.get("intent", "")).strip()
        transcript = str(payload.get("transcript", "")).strip()
        owner_id = str(payload.get("owner_id", "")).strip()
        telegram_chat_id = str(payload.get("telegram_chat_id", "")).strip()
        device_id = str(payload.get("device_id", "")).strip()
        session_id = str(payload.get("session_id", "")).strip()
        remote_job_id = str(payload.get("remote_job_id", "")).strip()
        metadata = dict(payload.get("metadata", {}))
        metadata.update(
            {
                "owner_id": owner_id,
                "telegram_chat_id": telegram_chat_id,
                "device_id": device_id,
                "session_id": session_id,
                "conversation_id": str(payload.get("conversation_id", "")).strip(),
                "battery_level": payload.get("battery_level"),
                "source_turn_id": turn_id,
            }
        )

        if intent == "capture_task":
            response = self._capture_task(
                transcript=transcript,
                owner_id=owner_id,
                telegram_chat_id=telegram_chat_id,
                metadata=metadata,
            )
        elif intent == "codex_handoff":
            response = self._codex_handoff(
                transcript=transcript,
                owner_id=owner_id,
                metadata=metadata,
            )
        elif intent == "status_query":
            response = self._status_query(
                remote_job_id=remote_job_id,
                owner_id=owner_id,
                device_id=device_id,
                session_id=session_id,
            )
        elif intent == "approval_action":
            response = self._approval_action(
                transcript=transcript,
                remote_job_id=remote_job_id,
                owner_id=owner_id,
                device_id=device_id,
                session_id=session_id,
            )
        elif intent == "handoff_long_reply":
            response = {
                "ok": True,
                "owner_id": owner_id,
                "remote_job_id": remote_job_id,
                "status": "accepted",
                "short_reply": "I handed that off to Telegram.",
                "long_reply_text": "",
                "long_reply_url": "",
                "needs_followup": False,
                "remote_request_id": turn_id or "",
            }
        else:
            raise ValueError(f"Unsupported companion intent: {intent}")

        self._store_request(request_id=request_id, payload=payload, response=response)
        return response

    def _capture_task(
        self,
        *,
        transcript: str,
        owner_id: str,
        telegram_chat_id: str,
        metadata: dict,
    ) -> dict:
        job = self.orchestrator.submit_job(
            workflow="inbox_capture",
            content=transcript or "Companion task capture.",
            source_channel="companion_remote",
            metadata=metadata,
        )
        summary = self._summary_text(job)
        short_reply = "I saved that for you."
        if job.status == "waiting_approval":
            short_reply = "I saved that. It needs your approval in Telegram."
        elif summary:
            short_reply = f"I saved that. {summary}"
        return {
            "ok": True,
            "owner_id": owner_id,
            "remote_job_id": job.id,
            "status": job.status,
            "short_reply": short_reply,
            "long_reply_text": self.orchestrator.format_status(job),
            "long_reply_url": "",
            "needs_followup": job.status == "waiting_approval",
            "remote_request_id": metadata.get("source_turn_id", ""),
        }

    def _codex_handoff(
        self,
        *,
        transcript: str,
        owner_id: str,
        metadata: dict,
    ) -> dict:
        metadata = {
            **metadata,
            "delegate_to": "codex",
            "codex_reasoning": "high",
            "spec_kit_required": True,
            "skip_flash_planning": True,
        }
        job = self.orchestrator.record_handoff_job(
            workflow="codex_handoff",
            content=transcript or "Codex coding handoff.",
            source_channel="companion_codex",
            metadata=metadata,
            summary="Coding request queued for Codex high-reasoning execution.",
        )
        return {
            "ok": True,
            "owner_id": owner_id,
            "remote_job_id": job.id,
            "status": job.status,
            "short_reply": "已自动交给 Codex。这个会走高推理编码流程，不用 Flash 做架构规划。",
            "long_reply_text": self.orchestrator.format_status(job),
            "long_reply_url": "",
            "needs_followup": True,
            "remote_request_id": metadata.get("source_turn_id", ""),
        }

    def _status_query(
        self,
        *,
        remote_job_id: str,
        owner_id: str,
        device_id: str,
        session_id: str,
    ) -> dict:
        job = self._resolve_job(remote_job_id=remote_job_id, device_id=device_id, session_id=session_id)
        if job is None:
            return {
                "ok": True,
                "owner_id": owner_id,
                "remote_job_id": "",
                "status": "not_found",
                "short_reply": "I could not find a recent Telegram task yet.",
                "long_reply_text": "",
                "long_reply_url": "",
                "needs_followup": False,
                "remote_request_id": "",
            }

        summary = self._summary_text(job)
        short_reply = f"The latest task is {job.status}."
        if summary:
            short_reply = f"The latest task is {job.status}. {summary}"
        return {
            "ok": True,
            "owner_id": owner_id,
            "remote_job_id": job.id,
            "status": job.status,
            "short_reply": short_reply,
            "long_reply_text": self.orchestrator.format_status(job),
            "long_reply_url": "",
            "needs_followup": job.status == "waiting_approval",
            "remote_request_id": "",
        }

    def _approval_action(
        self,
        *,
        transcript: str,
        remote_job_id: str,
        owner_id: str,
        device_id: str,
        session_id: str,
    ) -> dict:
        job = self._resolve_job(
            remote_job_id=remote_job_id,
            device_id=device_id,
            session_id=session_id,
            statuses={"waiting_approval"},
        )
        if job is None:
            return {
                "ok": True,
                "owner_id": owner_id,
                "remote_job_id": "",
                "status": "not_found",
                "short_reply": "I could not find anything waiting for approval.",
                "long_reply_text": "",
                "long_reply_url": "",
                "needs_followup": False,
                "remote_request_id": "",
            }

        lowered = transcript.lower()
        if any(token in lowered for token in self.REJECT_TOKENS):
            job = self.orchestrator.reject_job(job.id, "Rejected from companion intent API.")
            short_reply = "Rejected. I marked it as failed."
        else:
            job = self.orchestrator.approve_job(job.id, "Approved from companion intent API.")
            short_reply = "Approved. I pushed it forward."
        return {
            "ok": True,
            "owner_id": owner_id,
            "remote_job_id": job.id,
            "status": job.status,
            "short_reply": short_reply,
            "long_reply_text": self.orchestrator.format_status(job),
            "long_reply_url": "",
            "needs_followup": False,
            "remote_request_id": "",
        }

    def _resolve_job(
        self,
        *,
        remote_job_id: str,
        device_id: str,
        session_id: str,
        statuses: set[str] | None = None,
    ):
        if remote_job_id:
            try:
                job = self.orchestrator.get_job(remote_job_id)
            except KeyError:
                job = None
            if job is not None and (statuses is None or job.status in statuses):
                return job
        return self.orchestrator.find_recent_job(
            device_id=device_id,
            session_id=session_id,
            statuses=statuses,
        )

    def _summary_text(self, job) -> str:
        if not job.result:
            return ""
        return str(job.result.get("summary", "")).strip()

    def _request_id(self, turn_id: str) -> str:
        return f"companion_intent:{turn_id}" if turn_id else ""

    def _store_request(self, *, request_id: str, payload: dict, response: dict) -> None:
        if not request_id:
            return
        self.store.upsert(
            "messages",
            request_id,
            {
                "id": request_id,
                "channel": "companion_intent",
                "sender": payload.get("owner_id", "unknown"),
                "payload": payload,
                "reply": response.get("short_reply", ""),
                "job_id": response.get("remote_job_id"),
                "reply_payload": response,
            },
        )

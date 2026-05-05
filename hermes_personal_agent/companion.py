from __future__ import annotations

from hermes_personal_agent.orchestrator import TaskOrchestrator
from hermes_personal_agent.schemas import DeviceEvent
from hermes_personal_agent.storage import JsonStateStore


class CompanionService:
    def __init__(self, store: JsonStateStore, orchestrator: TaskOrchestrator) -> None:
        self.store = store
        self.orchestrator = orchestrator

    def ingest_event(self, payload: dict) -> dict:
        device_id = payload.get("device_id", "raspberry-pi")
        event_type = payload.get("event_type", "quick_note")
        event = DeviceEvent.create(device_id=device_id, event_type=event_type, payload=payload)
        self.store.upsert("device_events", event.id, event.to_dict())

        content = str(payload.get("text") or payload.get("transcript") or payload.get("note") or "").strip()
        if not content:
            content = f"Companion event received: {event_type}"

        workflow = "inbox_capture"
        metadata = {
            "device_id": device_id,
            "event_id": event.id,
            "offline_cached": bool(payload.get("offline_cached", False)),
        }

        if event_type == "photo_note":
            workflow = "knowledge_distill"
            metadata["has_image"] = True
        elif event_type == "voice_note":
            workflow = "inbox_capture"
        elif event_type == "quick_note":
            workflow = "inbox_capture"

        job = self.orchestrator.submit_job(
            workflow=workflow,
            content=content,
            source_channel="companion",
            metadata=metadata,
        )
        return {
            "event_id": event.id,
            "job_id": job.id,
            "status": job.status,
        }


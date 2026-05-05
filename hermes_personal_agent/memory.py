from __future__ import annotations

from hermes_personal_agent.schemas import JobRecord, MemoryCandidate, MemoryRecord, WorkflowResult
from hermes_personal_agent.storage import JsonStateStore


class MemoryManager:
    def __init__(self, store: JsonStateStore) -> None:
        self.store = store

    def create_candidate(self, job: JobRecord, result: WorkflowResult) -> MemoryCandidate:
        preferred_pattern = ", ".join(self._stringify_action(action) for action in result.actions[:3]) or "n/a"
        content = (
            f"Workflow: {job.workflow}\n"
            f"Summary: {result.summary}\n"
            f"Preferred Output Pattern: {preferred_pattern}"
        )
        candidate = MemoryCandidate.create(
            job_id=job.id,
            content=content,
            category="workflow_pattern",
            metadata={
                "source_channel": job.source_channel,
                "project": job.metadata.get("project", ""),
            },
        )
        self.store.upsert("memory_candidates", candidate.id, candidate.to_dict())
        return candidate

    def _stringify_action(self, action: object) -> str:
        if isinstance(action, str):
            return action
        if isinstance(action, dict):
            details = action.get("details")
            if isinstance(details, dict):
                for key in ("task_name", "title", "description"):
                    value = details.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            for key in ("action", "action_type", "title", "description"):
                value = action.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return str(action)

    def confirm_candidate(self, candidate_id: str) -> MemoryRecord:
        raw = self.store.get("memory_candidates", candidate_id)
        if raw is None:
            raise KeyError(f"Unknown memory candidate: {candidate_id}")
        candidate = MemoryCandidate.from_dict(raw)
        candidate.status = "confirmed"
        self.store.upsert("memory_candidates", candidate.id, candidate.to_dict())

        memory = MemoryRecord.create(
            content=candidate.content,
            category=candidate.category,
            source_candidate_id=candidate.id,
            metadata=candidate.metadata,
        )
        self.store.upsert("memories", memory.id, memory.to_dict())
        return memory

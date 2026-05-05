from __future__ import annotations

from hermes_personal_agent.memory import MemoryManager
from hermes_personal_agent.openrouter import ModelRouterAdapter
from hermes_personal_agent.schemas import JobRecord, JobStatus, WorkflowResult
from hermes_personal_agent.skills import SkillRegistry
from hermes_personal_agent.storage import JsonStateStore


class TaskOrchestrator:
    def __init__(
        self,
        store: JsonStateStore,
        models: ModelRouterAdapter,
        memory: MemoryManager,
        skills: SkillRegistry,
    ) -> None:
        self.store = store
        self.models = models
        self.memory = memory
        self.skills = skills

    def submit_job(
        self,
        workflow: str,
        content: str,
        source_channel: str,
        metadata: dict | None = None,
    ) -> JobRecord:
        job = JobRecord.create(
            workflow=workflow,
            content=content,
            source_channel=source_channel,
            metadata=metadata or {},
        )
        job.add_event("created", {"source_channel": source_channel})
        self._persist_job(job)

        skill = self.skills.match_by_workflow(workflow)
        if skill:
            job.add_event("skill_matched", {"skill": skill.name})
            self._persist_job(job)

        try:
            self._transition(job, JobStatus.PLANNED, "planned")
            self._transition(job, JobStatus.RUNNING, "running")
            result = self.models.run_workflow(workflow, content, job.metadata)
            job.result = result.to_dict()

            memory_candidate = self.memory.create_candidate(job, result)
            job.memory_candidate_ids.append(memory_candidate.id)

            next_state = JobStatus.WAITING_APPROVAL if result.needs_approval else JobStatus.DONE
            self._transition(
                job,
                next_state,
                "workflow_completed",
                {
                    "needs_approval": result.needs_approval,
                    "memory_candidate_id": memory_candidate.id,
                },
            )
            if skill:
                self.skills.record_use(skill.name, success=True)
            return job
        except Exception as exc:
            self._transition(job, JobStatus.FAILED, "workflow_failed", {"error": str(exc)})
            if skill:
                self.skills.record_use(skill.name, success=False)
            return job

    def record_handoff_job(
        self,
        workflow: str,
        content: str,
        source_channel: str,
        metadata: dict | None = None,
        summary: str = "",
    ) -> JobRecord:
        """Record a handoff without asking the lightweight planner to solve it."""
        job = JobRecord.create(
            workflow=workflow,
            content=content,
            source_channel=source_channel,
            metadata=metadata or {},
        )
        job.add_event("created", {"source_channel": source_channel})
        self._persist_job(job)
        self._transition(job, JobStatus.PLANNED, "handoff_recorded")
        job.result = WorkflowResult(
            summary=summary or f"Recorded handoff for {workflow}.",
            actions=["Delegate to Codex with high reasoning.", "Run project tests before reporting back."],
            open_questions=[],
            confidence=1.0,
            needs_approval=False,
            structured_payload={
                "delegate_to": "codex",
                "skip_lightweight_planning": True,
            },
            raw_response="handoff_recorded",
        ).to_dict()
        self._persist_job(job)
        return job

    def approve_job(self, job_id: str, comment: str = "") -> JobRecord:
        job = self.get_job(job_id)
        if job.status != JobStatus.WAITING_APPROVAL.value:
            raise ValueError(f"Job {job_id} is not waiting for approval.")
        self._transition(job, JobStatus.DONE, "approved", {"comment": comment})
        return job

    def reject_job(self, job_id: str, reason: str = "") -> JobRecord:
        job = self.get_job(job_id)
        if job.status != JobStatus.WAITING_APPROVAL.value:
            raise ValueError(f"Job {job_id} is not waiting for approval.")
        self._transition(job, JobStatus.FAILED, "rejected", {"reason": reason})
        return job

    def get_job(self, job_id: str) -> JobRecord:
        raw = self.store.get("jobs", job_id)
        if raw is None:
            raise KeyError(f"Unknown job: {job_id}")
        return JobRecord.from_dict(raw)

    def list_jobs(self) -> list[JobRecord]:
        jobs = [JobRecord.from_dict(item) for item in self.store.list("jobs")]
        jobs.sort(key=lambda job: (job.updated_at, job.created_at), reverse=True)
        return jobs

    def find_recent_job(
        self,
        *,
        device_id: str = "",
        session_id: str = "",
        statuses: set[str] | None = None,
    ) -> JobRecord | None:
        for job in self.list_jobs():
            if statuses is not None and job.status not in statuses:
                continue
            metadata = job.metadata or {}
            if device_id and metadata.get("device_id") == device_id:
                return job
            if session_id and metadata.get("session_id") == session_id:
                return job
        return None

    def _transition(
        self,
        job: JobRecord,
        status: JobStatus,
        event: str,
        payload: dict | None = None,
    ) -> None:
        job.status = status.value
        job.add_event(event, payload)
        self._persist_job(job)

    def _persist_job(self, job: JobRecord) -> None:
        self.store.upsert("jobs", job.id, job.to_dict())

    def format_status(self, job: JobRecord) -> str:
        result = WorkflowResult.from_dict(job.result) if job.result else None
        summary = result.summary if result else "No result yet."
        return (
            f"job={job.id}\n"
            f"workflow={job.workflow}\n"
            f"status={job.status}\n"
            f"summary={summary}"
        )

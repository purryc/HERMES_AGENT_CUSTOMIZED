from __future__ import annotations

from hermes_personal_agent.schemas import SkillTemplate, utc_now
from hermes_personal_agent.storage import JsonStateStore


DEFAULT_SKILLS = [
    SkillTemplate(
        name="Inbox Capture",
        workflow="inbox_capture",
        description="Turn raw messages into structured tasks, projects, and next actions.",
        version="1.0.0",
        active=True,
        phase="milestone_1",
        output_schema=["summary", "actions", "open_questions", "confidence", "needs_approval"],
    ),
    SkillTemplate(
        name="Drafting Assistant",
        workflow="drafting_assistant",
        description="Generate first drafts for emails, memos, meeting notes, and outlines.",
        version="1.0.0",
        active=True,
        phase="milestone_1",
        output_schema=["summary", "actions", "open_questions", "confidence", "needs_approval"],
    ),
    SkillTemplate(
        name="Knowledge Distill",
        workflow="knowledge_distill",
        description="Convert links, notes, and chats into searchable knowledge cards.",
        version="1.0.0",
        active=True,
        phase="milestone_1",
        output_schema=["summary", "actions", "open_questions", "confidence", "needs_approval"],
    ),
    SkillTemplate(
        name="Meeting Digest",
        workflow="knowledge_distill",
        description="Summarize meetings and generate follow-up tasks.",
        version="1.0.0",
        active=False,
        phase="milestone_1",
        output_schema=["summary", "actions", "open_questions", "confidence", "needs_approval"],
    ),
    SkillTemplate(
        name="Email First Draft",
        workflow="drafting_assistant",
        description="Create concise first-pass emails based on short prompts.",
        version="1.0.0",
        active=False,
        phase="milestone_1",
        output_schema=["summary", "actions", "open_questions", "confidence", "needs_approval"],
    ),
    SkillTemplate(
        name="Weekly Review",
        workflow="knowledge_distill",
        description="Compile updates, blockers, and decisions into a weekly review.",
        version="1.0.0",
        active=False,
        phase="milestone_2",
        output_schema=["summary", "actions", "open_questions", "confidence", "needs_approval"],
    ),
    SkillTemplate(
        name="Follow-up Builder",
        workflow="drafting_assistant",
        description="Prepare follow-up nudges and progress check-ins.",
        version="1.0.0",
        active=False,
        phase="milestone_2",
        output_schema=["summary", "actions", "open_questions", "confidence", "needs_approval"],
    ),
    SkillTemplate(
        name="Link Brief",
        workflow="knowledge_distill",
        description="Convert a raw link into a quick brief with action recommendations.",
        version="1.0.0",
        active=False,
        phase="milestone_2",
        output_schema=["summary", "actions", "open_questions", "confidence", "needs_approval"],
    ),
]


class SkillRegistry:
    def __init__(self, store: JsonStateStore) -> None:
        self.store = store
        self.ensure_defaults()

    def ensure_defaults(self) -> None:
        if self.store.list("skills"):
            return
        for skill in DEFAULT_SKILLS:
            self.store.upsert("skills", skill.name, skill.to_dict())

    def all(self) -> list[SkillTemplate]:
        return [SkillTemplate.from_dict(item) for item in self.store.list("skills")]

    def match_by_workflow(self, workflow: str) -> SkillTemplate | None:
        for skill in self.all():
            if skill.workflow == workflow and skill.active:
                return skill
        return None

    def record_use(self, skill_name: str, success: bool) -> None:
        raw = self.store.get("skills", skill_name)
        if raw is None:
            return
        skill = SkillTemplate.from_dict(raw)
        skill.usage_count += 1
        if success:
            skill.success_count += 1
        skill.last_used_at = utc_now()
        self.store.upsert("skills", skill.name, skill.to_dict())


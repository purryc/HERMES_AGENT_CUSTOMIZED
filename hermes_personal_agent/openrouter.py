from __future__ import annotations

from typing import Any
import json
import os
import urllib.error
import urllib.request

from hermes_personal_agent.config import ModelProfile
from hermes_personal_agent.schemas import WorkflowResult


class ModelRouterAdapter:
    def __init__(self, primary: ModelProfile, auxiliary: ModelProfile, vision: ModelProfile) -> None:
        self.primary = primary
        self.auxiliary = auxiliary
        self.vision = vision

    def select_profile(self, workflow: str, wants_vision: bool = False) -> ModelProfile:
        if wants_vision:
            return self.vision
        if workflow == "drafting_assistant":
            return self.primary
        return self.auxiliary

    def run_workflow(
        self,
        workflow: str,
        content: str,
        metadata: dict[str, Any],
    ) -> WorkflowResult:
        profile = self.select_profile(workflow, wants_vision=bool(metadata.get("has_image")))
        api_key = os.getenv(profile.api_key_env, "").strip()
        if not api_key:
            return self._mock_result(workflow, content, metadata)
        try:
            return self._call_openrouter(profile, workflow, content, metadata)
        except (urllib.error.URLError, TimeoutError, ValueError):
            return self._mock_result(workflow, content, metadata)

    def generate_companion_reply(
        self,
        transcript: str,
        conversation_history: list[dict[str, str]],
        metadata: dict[str, Any],
    ) -> str:
        return self.generate_brain_reply(
            channel="m5",
            user_text=transcript,
            conversation_history=conversation_history,
            context=metadata,
        )

    def generate_brain_reply(
        self,
        *,
        channel: str,
        user_text: str,
        conversation_history: list[dict[str, str]],
        context: dict[str, Any],
    ) -> str:
        profile = self.auxiliary if channel == "m5" else self.primary
        api_key = os.getenv(profile.api_key_env, "").strip()
        if not api_key:
            return self._mock_brain_reply(channel=channel, user_text=user_text, context=context)
        try:
            return self._call_brain_reply(
                profile=profile,
                channel=channel,
                user_text=user_text,
                conversation_history=conversation_history,
                context=context,
            )
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
            return self._mock_brain_reply(channel=channel, user_text=user_text, context=context)

    def _call_openrouter(
        self,
        profile: ModelProfile,
        workflow: str,
        content: str,
        metadata: dict[str, Any],
    ) -> WorkflowResult:
        system_prompt = (
            "You are an execution engine for a personal work agent. "
            "Return only valid JSON with keys: summary, actions, open_questions, "
            "confidence, needs_approval, structured_payload."
        )
        user_prompt = {
            "workflow": workflow,
            "content": content,
            "metadata": metadata,
            "policy": {
                "human_in_the_loop": True,
                "approve_for_high_risk": True,
            },
        }
        body = {
            "model": profile.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
        }
        encoded = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            profile.base_url,
            data=encoded,
            headers={
                "Authorization": f"Bearer {os.getenv(profile.api_key_env, '')}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://local.hermes-personal-agent",
                "X-Title": "Hermes Personal Work Agent Starter",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=profile.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        message = self._extract_message_text(payload["choices"][0]["message"]["content"])
        parsed = json.loads(message)
        return WorkflowResult(
            summary=parsed["summary"],
            actions=list(parsed.get("actions", [])),
            open_questions=list(parsed.get("open_questions", [])),
            confidence=float(parsed.get("confidence", 0.5)),
            needs_approval=bool(parsed.get("needs_approval", False)),
            structured_payload=dict(parsed.get("structured_payload", {})),
            raw_response=message,
        )

    def _call_brain_reply(
        self,
        *,
        profile: ModelProfile,
        channel: str,
        user_text: str,
        conversation_history: list[dict[str, str]],
        context: dict[str, Any],
    ) -> str:
        if channel == "m5":
            system_prompt = (
                "You are Hermes CEO Agent speaking through a tiny pet device. "
                "Reply in concise natural Mandarin, usually within 2-4 short sentences. "
                "Be warm, short, supportive, and audio-friendly. Do not use markdown or bullet lists."
            )
        else:
            system_prompt = (
                "You are Hermes CEO Agent speaking in Telegram. "
                "Reply in clear, operational Mandarin. "
                "You may be concise or moderately detailed depending on the request. "
                "Do not use markdown tables."
            )
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for item in conversation_history[-12:]:
            role = item.get("role", "user")
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        prompt_context = json.dumps(context, ensure_ascii=False)
        messages.append(
            {
                "role": "user",
                "content": f"{user_text.strip() or '和我打个招呼。'}\n\nShared context: {prompt_context}",
            }
        )
        body = {
            "model": profile.model,
            "messages": messages,
        }
        encoded = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            profile.base_url,
            data=encoded,
            headers={
                "Authorization": f"Bearer {os.getenv(profile.api_key_env, '')}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://local.hermes-personal-agent",
                "X-Title": "Hermes CEO Agent Host",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=profile.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return self._extract_message_text(payload["choices"][0]["message"]["content"]).strip()

    def _mock_result(
        self,
        workflow: str,
        content: str,
        metadata: dict[str, Any],
    ) -> WorkflowResult:
        high_risk = bool(set(metadata.get("requested_actions", [])) & {"file_write", "browser_automation", "external_send"})
        summary = content.strip().replace("\n", " ")
        if len(summary) > 140:
            summary = summary[:137] + "..."

        if workflow == "inbox_capture":
            project = metadata.get("project") or self._guess_project(content)
            actions = self._extract_actions(content)
            return WorkflowResult(
                summary=f"Captured work item: {summary}",
                actions=actions or ["Review the item and assign an owner/timebox."],
                open_questions=self._extract_questions(content),
                confidence=0.72,
                needs_approval=high_risk,
                structured_payload={
                    "priority": self._guess_priority(content),
                    "project": project,
                    "tags": self._guess_tags(content),
                    "next_step": actions[0] if actions else "Clarify the expected deliverable.",
                },
                raw_response="mock",
            )

        if workflow == "drafting_assistant":
            draft = (
                "Subject: Progress update\n\n"
                f"Here is a working draft based on your request:\n{content.strip()}\n\n"
                "Current status: the first milestone is scoped, the system boundaries are clear, "
                "and the next step is wiring the messaging and approval loop."
            )
            return WorkflowResult(
                summary=f"Draft prepared for: {summary}",
                actions=["Review tone and recipients.", "Add missing facts or dates.", "Approve before sending externally."],
                open_questions=["Who is the audience?", "Should the tone stay direct or become more formal?"],
                confidence=0.68,
                needs_approval=True if "send" in content.lower() or high_risk else False,
                structured_payload={
                    "draft_type": "message_or_memo",
                    "tone": "direct",
                    "draft": draft,
                },
                raw_response="mock",
            )

        knowledge_cards = [
            {
                "title": "Primary insight",
                "content": summary,
            },
            {
                "title": "Suggested next move",
                "content": "Turn the distilled material into a reusable note, checklist, or operating decision.",
            },
        ]
        return WorkflowResult(
            summary=f"Knowledge distilled from: {summary}",
            actions=["Save the top insight into the knowledge base.", "Link it to the active project.", "Decide whether follow-up is needed."],
            open_questions=self._extract_questions(content),
            confidence=0.74,
            needs_approval=high_risk,
            structured_payload={
                "knowledge_cards": knowledge_cards,
                "search_terms": self._guess_tags(content),
            },
            raw_response="mock",
        )

    def _mock_brain_reply(self, *, channel: str, user_text: str, context: dict[str, Any]) -> str:
        text = user_text.strip()
        memories = [str(item).strip() for item in context.get("memories", []) if str(item).strip()]
        memory_hint = memories[0][:32] if memories else ""
        if channel == "m5":
            if not text:
                return "我在呢，按住按钮和我说话吧。"
            if any(token in text.lower() for token in ["hello", "hi"]) or "你好" in text:
                return "你好呀，我已经在这儿了。今天想让我陪你做什么？"
            if memory_hint:
                return f"我记得你最近在想“{memory_hint}”。刚才这句我也接住了。"
            if context.get("recent_jobs"):
                return "我接住了，这件事和你最近的任务是连着的。"
            return f"我听见啦。关于“{text[:24]}”，我可以继续陪你聊，也可以帮你记下来。"

        if not text:
            return "我在线。你可以直接交代任务，或者继续我们刚才的话题。"
        if memory_hint:
            return f"我记得你最近在处理“{memory_hint}”。结合你刚才这句，我建议先把目标和下一步定清楚。"
        if context.get("recent_jobs"):
            latest = context["recent_jobs"][0]
            return (
                f"我在看着你的任务池。最新一项是 {latest.get('job_id', '')}，状态 {latest.get('status', 'unknown')}。"
                f" 对于“{text[:30]}”，我可以直接继续帮你推进。"
            )
        return f"我收到你的意思了。关于“{text[:30]}”，我可以直接帮你拆成任务、起草回复，或者先给你建议。"

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

    def _extract_actions(self, content: str) -> list[str]:
        lines = [line.strip("-* \t") for line in content.splitlines() if line.strip()]
        if len(lines) > 1:
            return [line for line in lines[:3]]
        fragments = [item.strip() for item in content.replace("，", ",").split(",") if item.strip()]
        return fragments[:3]

    def _extract_questions(self, content: str) -> list[str]:
        questions = []
        normalized = content.replace("？", "?")
        for piece in normalized.split("?"):
            text = piece.strip()
            if text and "?" in normalized:
                questions.append(" ".join(text.split()[-6:]).strip())
        return questions[:3]

    def _guess_priority(self, content: str) -> str:
        lowered = content.lower()
        if any(word in lowered for word in ["today", "urgent", "asap", "马上", "今天"]):
            return "high"
        if any(word in lowered for word in ["this week", "本周", "周三", "tomorrow", "明天"]):
            return "medium"
        return "normal"

    def _guess_project(self, content: str) -> str:
        lowered = content.lower()
        if "hermes" in lowered:
            return "hermes-agent"
        if "wechat" in lowered or "wecom" in lowered or "telegram" in lowered:
            return "messaging-gateway"
        return "general"

    def _guess_tags(self, content: str) -> list[str]:
        tags = []
        lowered = content.lower()
        for keyword in ["hermes", "openrouter", "wechat", "wecom", "telegram", "raspberry pi", "dashboard", "memory"]:
            if keyword in lowered:
                tags.append(keyword.replace(" ", "_"))
        return tags or ["general"]

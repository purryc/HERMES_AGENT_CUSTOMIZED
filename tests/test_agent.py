from __future__ import annotations

from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import wave
from io import BytesIO
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from xml.etree import ElementTree as ET

from hermes_personal_agent.cli import build_services
from hermes_personal_agent.schemas import MemoryCandidate, MemoryRecord, VoiceTurnRecord, WorkflowResult
from hermes_personal_agent.server import build_handler


class AgentStarterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_cwd = Path.cwd()
        self._saved_env = {
            key: os.environ.get(key)
            for key in [
                "OPENROUTER_API_KEY",
                "WECOM_TOKEN",
                "WECOM_ENCODING_AES_KEY",
                "WECOM_CORP_ID",
                "WECOM_AGENT_ID",
                "MAIN_BRAIN_AUTH_TOKEN",
            ]
        }
        for key in self._saved_env:
            os.environ.pop(key, None)

        self.temp_dir = Path(tempfile.mkdtemp(prefix="agent-starter-"))
        os.chdir(self.temp_dir)
        self.config_path = self.temp_dir / "config.json"
        self._main_brain_servers: list[tuple[ThreadingHTTPServer, threading.Thread]] = []
        self._write_config()
        _, self.services = build_services(str(self.config_path))
        self.http_server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(self.services))
        self.server_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.server_thread.start()
        self.base_url = f"http://127.0.0.1:{self.http_server.server_address[1]}"

    def tearDown(self) -> None:
        self.http_server.shutdown()
        self.http_server.server_close()
        self.server_thread.join(timeout=2)
        for server, thread in self._main_brain_servers:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        os.chdir(self._saved_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_sqlite_is_default_store(self) -> None:
        self.assertTrue((self.temp_dir / "data" / "state.db").exists())

    def test_submit_job_persists_and_returns_protocol(self) -> None:
        job = self.services.orchestrator.submit_job(
            workflow="inbox_capture",
            content="Finish the Hermes plus OpenRouter MVP this week and list the top risks.",
            source_channel="terminal",
            metadata={"project": "personal-agent"},
        )
        self.assertIn(job.status, {"done", "waiting_approval"})
        self.assertIsNotNone(job.result)
        self.assertIn("summary", job.result)
        self.assertIn("actions", job.result)
        self.assertTrue(job.memory_candidate_ids)

    def test_message_deduplication(self) -> None:
        payload = {"message_id": "wx-001", "text": "draft: write a short status update", "sender": "me"}
        first = self.services.messaging.ingest("wechat", payload)
        second = self.services.messaging.ingest("wechat", payload)
        self.assertFalse(first["deduplicated"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(first["job_id"], second["job_id"])

    def test_telegram_message_endpoint_creates_job(self) -> None:
        payload = self._post_json(
            "/api/messages/telegram",
            {
                "message_id": "tg-001",
                "text": "distill: summarize today's OpenRouter model routing notes",
                "sender": "me",
                "telegram_chat_id": "tg-123",
            },
        )
        self.assertFalse(payload["deduplicated"])
        job = self.services.orchestrator.get_job(payload["job_id"])
        self.assertEqual(job.source_channel, "telegram")
        self.assertEqual(job.workflow, "knowledge_distill")

    def test_telegram_plain_text_creates_conversation_thread(self) -> None:
        payload = self._post_json(
            "/api/messages/telegram",
            {
                "message_id": "tg-chat-001",
                "text": "我们今天先把 CEO Agent 的任务边界定一下。",
                "sender": "me",
                "telegram_chat_id": "tg-123",
                "owner_id": "owner_you",
            },
        )
        self.assertEqual(payload["mode"], "conversation")
        self.assertTrue(payload["conversation_id"])
        self.assertTrue(payload["reply_text"])
        conversations = self.services.brain.store.list("conversations")
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]["channel"], "telegram")
        self.assertEqual(conversations[0]["owner_id"], "owner_you")

    def test_telegram_jobs_command_returns_recent_jobs(self) -> None:
        self.services.orchestrator.submit_job(
            workflow="inbox_capture",
            content="Create a Telegram-visible task.",
            source_channel="telegram",
            metadata={"owner_id": "owner_you", "telegram_chat_id": "tg-123"},
        )
        payload = self._post_json(
            "/api/messages/telegram",
            {
                "message_id": "tg-jobs-001",
                "text": "/jobs",
                "sender": "me",
                "telegram_chat_id": "tg-123",
                "owner_id": "owner_you",
            },
        )
        self.assertEqual(payload["mode"], "jobs")
        self.assertIn("recent jobs", payload["reply_text"])
        self.assertIn("job_", payload["long_reply_text"])

    def test_approval_flow(self) -> None:
        job = self.services.orchestrator.submit_job(
            workflow="drafting_assistant",
            content="Please draft and send a partner update.",
            source_channel="wechat",
            metadata={"requested_actions": ["external_send"]},
        )
        self.assertEqual(job.status, "waiting_approval")
        approved = self.services.orchestrator.approve_job(job.id, "looks good")
        self.assertEqual(approved.status, "done")

    def test_companion_event_creates_job(self) -> None:
        result = self.services.companion.ingest_event(
            {
                "device_id": "pi-zero-01",
                "event_type": "photo_note",
                "text": "Turn this whiteboard snapshot into action items.",
            }
        )
        self.assertIn("job_id", result)
        job = self.services.orchestrator.get_job(result["job_id"])
        self.assertEqual(job.source_channel, "companion")

    def test_memory_candidate_handles_structured_actions(self) -> None:
        job = self.services.orchestrator.submit_job(
            workflow="inbox_capture",
            content="Baseline job for memory candidate formatting.",
            source_channel="terminal",
            metadata={"project": "memory-test"},
        )
        result = WorkflowResult(
            summary="Structured action test.",
            actions=[
                {
                    "action_type": "create_task",
                    "details": {"task_name": "Wire the voice router"},
                }
            ],
            open_questions=[],
            confidence=0.9,
            needs_approval=False,
            structured_payload={},
        )
        candidate = self.services.memory.create_candidate(job, result)
        self.assertIn("Wire the voice router", candidate.content)

    def test_config_loads_env_file_without_overwriting_existing_env(self) -> None:
        env_path = self.temp_dir / ".env"
        env_path.write_text("OPENROUTER_API_KEY=from-env-file\n", encoding="utf-8")

        previous = os.environ.get("OPENROUTER_API_KEY")
        os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            _, services = build_services(str(self.config_path))
            self.assertIsNotNone(services)
            self.assertEqual(os.environ.get("OPENROUTER_API_KEY"), "from-env-file")

            os.environ["OPENROUTER_API_KEY"] = "already-set"
            _, services = build_services(str(self.config_path))
            self.assertIsNotNone(services)
            self.assertEqual(os.environ.get("OPENROUTER_API_KEY"), "already-set")
        finally:
            if previous is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = previous

    def test_wecom_verify_url_roundtrip(self) -> None:
        crypto = self.services.wecom.crypto
        self.assertIsNotNone(crypto)
        assert crypto is not None
        timestamp = str(int(time.time()))
        nonce = "n-verify"
        plaintext = "verify-ok"
        echostr = crypto._encrypt(plaintext)
        signature = crypto._signature(timestamp, nonce, echostr)

        verified = self.services.wecom.verify_url(
            {
                "msg_signature": signature,
                "timestamp": timestamp,
                "nonce": nonce,
                "echostr": echostr,
            }
        )
        self.assertEqual(verified, plaintext)

    def test_wecom_encrypted_text_callback_creates_job(self) -> None:
        crypto = self.services.wecom.crypto
        self.assertIsNotNone(crypto)
        assert crypto is not None
        timestamp = str(int(time.time()))
        nonce = "n-callback"
        plaintext = (
            "<xml>"
            "<ToUserName><![CDATA[ww1234567890abcd]]></ToUserName>"
            "<FromUserName><![CDATA[zhangsan]]></FromUserName>"
            "<CreateTime>1713744000</CreateTime>"
            "<MsgType><![CDATA[text]]></MsgType>"
            "<Content><![CDATA[draft: write a short update for the Hermes rollout]]></Content>"
            "<MsgId>900001</MsgId>"
            "<AgentID>1000002</AgentID>"
            "</xml>"
        )
        xml_body = crypto.encrypt_message(plaintext, timestamp, nonce)
        encrypted = ET.fromstring(xml_body).findtext("Encrypt", "")
        signature = crypto._signature(timestamp, nonce, encrypted)

        result = self.services.wecom.handle_callback(
            {
                "msg_signature": signature,
                "timestamp": timestamp,
                "nonce": nonce,
            },
            xml_body,
        )
        self.assertTrue(result["handled"])
        self.assertFalse(result["ignored"])
        job = self.services.orchestrator.get_job(result["job_id"])
        self.assertEqual(job.source_channel, "wecom")
        self.assertEqual(job.workflow, "drafting_assistant")

    def test_voice_turn_upload_poll_audio_and_repeat_fetch(self) -> None:
        wav_bytes = self._make_test_wav(duration_seconds=1.1)
        payload = self._multipart_body(
            fields={
                "device_id": "stick-s3-01",
                "session_id": "pet-session",
                "battery_level": "82",
            },
            files={
                "audio": {
                    "filename": "turn.wav",
                    "content_type": "audio/wav",
                    "content": wav_bytes,
                }
            },
        )
        request = urllib.request.Request(
            f"{self.base_url}/api/companion/voice-turns",
            data=payload["body"],
            headers={"Content-Type": payload["content_type"]},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            created = json.loads(response.read().decode("utf-8"))

        self.assertEqual(created["status"], "processing")
        turn_id = created["turn_id"]
        polled = self._wait_for_voice_turn(turn_id)
        self.assertEqual(polled["status"], "done")
        self.assertTrue(polled["transcript"])
        self.assertTrue(polled["reply_text"])
        self.assertIn(polled["emotion"], {"neutral", "happy", "curious", "sleepy", "sad", "excited"})
        self.assertEqual(polled["expression"], "speaking")
        self.assertTrue(polled["audio_url"])

        with urllib.request.urlopen(f"{self.base_url}{polled['audio_url']}", timeout=10) as response:
            audio_bytes = response.read()
            content_type = response.headers.get_content_type()

        self.assertEqual(content_type, "audio/wav")
        self.assertGreater(len(audio_bytes), 44)

        with urllib.request.urlopen(f"{self.base_url}/api/companion/voice-turns/{turn_id}", timeout=10) as response:
            second_fetch = json.loads(response.read().decode("utf-8"))
        self.assertEqual(polled, second_fetch)

    def test_voice_turn_cleanup_removes_expired_audio_without_touching_processing_turn(self) -> None:
        wav_bytes = self._make_test_wav(duration_seconds=1.0)
        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="cleanup-session",
            audio_bytes=wav_bytes,
            battery_level=50,
        )
        finished = self._wait_for_voice_turn_record(turn.id)
        self.assertEqual(finished.status, "done")
        self.assertTrue(finished.audio_asset_id)

        asset = self.services.voice_turns.store.get("audio_assets", finished.audio_asset_id)
        self.assertIsNotNone(asset)
        assert asset is not None
        asset["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        self.services.voice_turns.store.upsert("audio_assets", asset["id"], asset)

        processing_turn = VoiceTurnRecord.create(
            device_id="stick-s3-01",
            session_id="cleanup-session-2",
            conversation_id="conv_processing",
            battery_level=None,
        )
        self.services.voice_turns.store.upsert("voice_turns", processing_turn.id, processing_turn.to_dict())

        removed = self.services.voice_turns.cleanup_expired_assets()
        self.assertEqual(removed, 1)
        self.assertFalse(self.services.voice_turns.store.exists("audio_assets", asset["id"]))
        still_processing = self.services.voice_turns.get_turn(processing_turn.id)
        self.assertEqual(still_processing.status, "processing")

    def test_voice_turn_capture_task_routes_into_shared_job_pool(self) -> None:
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "记一下，明天测试 M5 和 Telegram 的统一任务流。"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=81,
        )
        finished = self._wait_for_voice_turn_record(turn.id)
        self.assertEqual(finished.intent, "capture_task")
        self.assertTrue(finished.linked_job_id)

        job = self.services.orchestrator.get_job(finished.linked_job_id)
        self.assertEqual(job.source_channel, "companion_remote")
        self.assertEqual(job.metadata["device_id"], "stick-s3-01")

    def test_voice_turn_status_query_reads_recent_job(self) -> None:
        job = self.services.orchestrator.submit_job(
            workflow="inbox_capture",
            content="Remember to verify the Telegram route.",
            source_channel="companion_remote",
            metadata={"device_id": "stick-s3-01", "session_id": "pet-session"},
        )
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "刚才那个任务做到哪了？"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=70,
        )
        finished = self._wait_for_voice_turn_record(turn.id)
        self.assertEqual(finished.intent, "status_query")
        self.assertEqual(finished.linked_job_id, job.id)
        self.assertIn(job.status, finished.reply_text)

    def test_voice_turn_web_search_opens_desktop_browser(self) -> None:
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "帮我上网搜索APPLE 股价"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        opened_urls: list[str] = []

        def fake_open(url: str, new: int = 0) -> bool:
            opened_urls.append(url)
            return True

        with patch("hermes_personal_agent.voice_turns.webbrowser.open", side_effect=fake_open):
            turn = self.services.voice_turns.create_turn_from_upload(
                device_id="stick-s3-01",
                session_id="pet-session",
                audio_bytes=self._make_test_wav(duration_seconds=0.8),
                battery_level=70,
            )
            finished = self._wait_for_voice_turn_record(turn.id)

        self.assertEqual(finished.intent, "open_browser_search")
        self.assertEqual(opened_urls, ["https://www.google.com/search?q=APPLE+%E8%82%A1%E4%BB%B7"])
        self.assertIn("APPLE 股价", finished.reply_text)
        self.assertTrue(
            any(event["event"] == "desktop_browser_opened" for event in finished.event_log)
        )

    def test_companion_text_turn_endpoint_persists_dashboard_message(self) -> None:
        self.services.brain.models.generate_brain_reply = (
            lambda **_kwargs: "Dashboard reply recorded."
        )

        payload = self._post_json(
            "/api/companion/text-turns",
            {
                "device_id": "m5stick-s3-pet-01",
                "session_id": "main-session",
                "text": "Continue from the dashboard.",
            },
        )

        self.assertEqual(payload["status"], "done")
        self.assertEqual(payload["transcript"], "Continue from the dashboard.")
        self.assertEqual(payload["reply_text"], "Dashboard reply recorded.")
        self.assertEqual(payload["attachments"], [])

        turn = self.services.voice_turns.get_turn(payload["turn_id"])
        self.assertEqual(turn.status, "done")
        self.assertEqual(turn.transcript, "Continue from the dashboard.")
        self.assertTrue(any(event["payload"].get("source") == "dashboard" for event in turn.event_log))

        session = self.services.voice_turns.store.get("companion_sessions", "main-session")
        self.assertIsNotNone(session)
        assert session is not None
        self.assertEqual(session["last_turn_id"], payload["turn_id"])
        self.assertEqual(session["recent_turns"][-2]["content"], "Continue from the dashboard.")
        self.assertEqual(session["recent_turns"][-1]["content"], "Dashboard reply recorded.")

    def test_companion_text_turn_endpoint_validates_attachment_metadata(self) -> None:
        self.services.brain.models.generate_brain_reply = (
            lambda **_kwargs: "I saw the attachment metadata."
        )

        payload = self._post_json(
            "/api/companion/text-turns",
            {
                "device_id": "m5stick-s3-pet-01",
                "session_id": "main-session",
                "text": "Here is context.",
                "attachments": [
                    {
                        "filename": "../photo.png",
                        "content_type": "image/png",
                        "size_bytes": 1234,
                    }
                ],
            },
        )

        self.assertEqual(payload["status"], "done")
        self.assertEqual(payload["attachments"][0]["filename"], "photo.png")
        self.assertEqual(payload["attachments"][0]["content_type"], "image/png")

        request = urllib.request.Request(
            f"{self.base_url}/api/companion/text-turns",
            data=json.dumps(
                {
                    "device_id": "m5stick-s3-pet-01",
                    "session_id": "main-session",
                    "text": "",
                    "attachments": [
                        {
                            "filename": "script.exe",
                            "content_type": "application/x-msdownload",
                            "size_bytes": 100,
                        }
                    ],
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(ctx.exception.code, 400)

    def test_companion_text_turn_coding_request_records_codex_handoff_without_planner(self) -> None:
        def fail_if_lightweight_planner_runs(*_args, **_kwargs):
            raise AssertionError("coding handoff should not use lightweight workflow planning")

        self.services.orchestrator.models.run_workflow = fail_if_lightweight_planner_runs

        payload = self._post_json(
            "/api/companion/text-turns",
            {
                "device_id": "m5stick-s3-pet-01",
                "session_id": "main-session",
                "text": "让 Codex 帮我在 Dividend Dashboard 里实现分红日历并跑测试",
            },
        )

        self.assertEqual(payload["status"], "done")
        self.assertEqual(payload["intent"], "codex_handoff")
        self.assertTrue(payload["linked_job_id"])
        self.assertTrue(payload["needs_followup"])

        job = self.services.orchestrator.get_job(payload["linked_job_id"])
        self.assertEqual(job.workflow, "codex_handoff")
        self.assertEqual(job.source_channel, "companion_codex")
        self.assertEqual(job.status, "planned")
        self.assertEqual(job.metadata["delegate_to"], "codex")
        self.assertEqual(job.metadata["codex_reasoning"], "high")
        self.assertTrue(job.metadata["spec_kit_required"])
        self.assertTrue(job.metadata["skip_flash_planning"])

    def test_voice_turn_approval_action_resolves_waiting_job(self) -> None:
        job = self.services.orchestrator.submit_job(
            workflow="drafting_assistant",
            content="Please draft and send the customer summary.",
            source_channel="companion_remote",
            metadata={
                "device_id": "stick-s3-01",
                "session_id": "pet-session",
                "requested_actions": ["external_send"],
            },
        )
        self.assertEqual(job.status, "waiting_approval")

        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "好，这个通过吧。"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=64,
        )
        finished = self._wait_for_voice_turn_record(turn.id)
        approved = self.services.orchestrator.get_job(job.id)
        self.assertEqual(finished.intent, "approval_action")
        self.assertEqual(finished.linked_job_id, job.id)
        self.assertEqual(approved.status, "done")

    def test_voice_turn_companion_chat_uses_brain_and_shared_memory(self) -> None:
        memory = MemoryRecord.create(
            content="User prefers Telegram as the approval console.",
            category="workflow_pattern",
            source_candidate_id="seed",
            metadata={},
        )
        self.services.brain.store.upsert("memories", memory.id, memory.to_dict())
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "今天我们先聊聊下一步。"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=88,
        )
        finished = self._wait_for_voice_turn_record(turn.id)

        self.assertEqual(finished.intent, "companion_chat")
        self.assertIn("Telegram", finished.reply_text)
        conversations = self.services.brain.store.list("conversations")
        self.assertTrue(any(item["channel"] == "m5" for item in conversations))

    def test_companion_intent_capture_endpoint_returns_standard_payload(self) -> None:
        payload = self._post_json(
            "/api/companion/intents",
            {
                "intent": "capture_task",
                "transcript": "记一下，今晚把桌面 UI 方案发到 Telegram。",
                "owner_id": "owner_you",
                "telegram_chat_id": "tg-123",
                "device_id": "stick-s3-01",
                "session_id": "pet-session",
                "conversation_id": "conv-001",
                "battery_level": 82,
                "turn_id": "turn-001",
                "metadata": {"source": "m5_companion"},
            },
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["owner_id"], "owner_you")
        self.assertTrue(payload["remote_job_id"])
        self.assertIn(payload["status"], {"done", "waiting_approval"})
        self.assertTrue(payload["short_reply"])
        self.assertIn("job=", payload["long_reply_text"])

        job = self.services.orchestrator.get_job(payload["remote_job_id"])
        self.assertEqual(job.source_channel, "companion_remote")
        self.assertEqual(job.metadata["telegram_chat_id"], "tg-123")
        self.assertEqual(job.metadata["device_id"], "stick-s3-01")

    def test_companion_intent_status_and_approval_endpoint(self) -> None:
        waiting_job = self.services.orchestrator.submit_job(
            workflow="drafting_assistant",
            content="Please draft and send the customer summary.",
            source_channel="telegram",
            metadata={
                "device_id": "stick-s3-01",
                "session_id": "pet-session",
                "requested_actions": ["external_send"],
            },
        )
        self.assertEqual(waiting_job.status, "waiting_approval")

        status_payload = self._post_json(
            "/api/companion/intents",
            {
                "intent": "status_query",
                "transcript": "刚才那个任务做到哪了？",
                "owner_id": "owner_you",
                "telegram_chat_id": "tg-123",
                "device_id": "stick-s3-01",
                "session_id": "pet-session",
                "remote_job_id": waiting_job.id,
                "turn_id": "turn-002",
            },
        )
        self.assertTrue(status_payload["ok"])
        self.assertEqual(status_payload["remote_job_id"], waiting_job.id)
        self.assertEqual(status_payload["status"], "waiting_approval")

        approve_payload = self._post_json(
            "/api/companion/intents",
            {
                "intent": "approval_action",
                "transcript": "好，这个通过吧。",
                "owner_id": "owner_you",
                "telegram_chat_id": "tg-123",
                "device_id": "stick-s3-01",
                "session_id": "pet-session",
                "remote_job_id": waiting_job.id,
                "turn_id": "turn-003",
            },
        )
        self.assertTrue(approve_payload["ok"])
        self.assertEqual(approve_payload["remote_job_id"], waiting_job.id)
        self.assertEqual(approve_payload["status"], "done")
        updated = self.services.orchestrator.get_job(waiting_job.id)
        self.assertEqual(updated.status, "done")

    def test_companion_intent_endpoint_is_idempotent_by_turn_id(self) -> None:
        body = {
            "intent": "capture_task",
            "transcript": "记一下，明天检查主脑路由。",
            "owner_id": "owner_you",
            "telegram_chat_id": "tg-123",
            "device_id": "stick-s3-01",
            "session_id": "pet-session",
            "turn_id": "turn-dedupe-001",
        }
        first_payload = self._post_json("/api/companion/intents", body)
        second_payload = self._post_json("/api/companion/intents", body)
        self.assertEqual(first_payload, second_payload)
        self.assertEqual(len(self.services.orchestrator.list_jobs()), 1)

    def test_voice_turn_capture_task_forwards_to_external_main_brain(self) -> None:
        calls: list[dict] = []

        def responder(payload: dict) -> dict:
            calls.append(payload)
            return {
                "ok": True,
                "owner_id": payload["owner_id"],
                "remote_job_id": "remote_job_001",
                "status": "planned",
                "short_reply": "I saved that for you.",
                "long_reply_text": "",
                "long_reply_url": "",
                "needs_followup": False,
                "remote_request_id": "req_001",
            }

        base_url = self._start_main_brain_server(responder)
        self._rebuild_services(
            {
                "main_brain": {
                    "enabled": True,
                    "base_url": base_url,
                    "owner_id": "owner_you",
                    "telegram_chat_id": "tg-123",
                    "timeout_seconds": 2,
                }
            }
        )
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "记一下，晚上把桌面 UI 架构发到 Telegram。"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=88,
        )
        finished = self._wait_for_voice_turn_record(turn.id)

        self.assertEqual(finished.intent, "capture_task")
        self.assertEqual(finished.owner_id, "owner_you")
        self.assertEqual(finished.linked_job_id, "remote_job_001")
        self.assertEqual(finished.remote_job_id, "remote_job_001")
        self.assertEqual(finished.remote_status, "planned")
        self.assertEqual(finished.remote_request_id, "req_001")
        self.assertFalse(finished.handoff_queued)
        self.assertEqual(len(self.services.orchestrator.list_jobs()), 0)
        self.assertEqual(len(calls), 1)

    def test_voice_turn_coding_request_forwards_to_external_main_brain_as_codex_handoff(self) -> None:
        calls: list[dict] = []

        def responder(payload: dict) -> dict:
            calls.append(payload)
            self.assertEqual(payload["intent"], "codex_handoff")
            self.assertEqual(payload["metadata"]["delegate_to"], "codex")
            self.assertEqual(payload["metadata"]["codex_reasoning"], "high")
            self.assertTrue(payload["metadata"]["spec_kit_required"])
            self.assertTrue(payload["metadata"]["skip_flash_planning"])
            return {
                "ok": True,
                "owner_id": payload["owner_id"],
                "remote_job_id": "codex_job_001",
                "status": "running",
                "short_reply": "I handed that to Codex high reasoning.",
                "long_reply_text": "",
                "long_reply_url": "",
                "needs_followup": True,
                "remote_request_id": "req_codex_001",
            }

        base_url = self._start_main_brain_server(responder)
        self._rebuild_services(
            {
                "main_brain": {
                    "enabled": True,
                    "base_url": base_url,
                    "owner_id": "owner_you",
                    "telegram_chat_id": "tg-123",
                    "timeout_seconds": 2,
                }
            }
        )
        self.services.voice_turns.speech.transcribe = (
            lambda *_args, **_kwargs: "让 Codex 帮我修 dashboard chat 页面并跑测试"
        )
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=88,
        )
        finished = self._wait_for_voice_turn_record(turn.id)

        self.assertEqual(finished.intent, "codex_handoff")
        self.assertEqual(finished.owner_id, "owner_you")
        self.assertEqual(finished.linked_job_id, "codex_job_001")
        self.assertEqual(finished.remote_job_id, "codex_job_001")
        self.assertEqual(finished.remote_status, "running")
        self.assertEqual(finished.remote_request_id, "req_codex_001")
        self.assertFalse(finished.handoff_queued)
        self.assertEqual(len(self.services.orchestrator.list_jobs()), 0)
        self.assertEqual(len(calls), 1)

    def test_voice_turn_status_and_approval_forward_to_external_main_brain(self) -> None:
        calls: list[dict] = []

        def responder(payload: dict) -> dict:
            calls.append(payload)
            transcript = payload["transcript"]
            if payload["intent"] == "capture_task":
                return {
                    "ok": True,
                    "owner_id": "owner_you",
                    "remote_job_id": "remote_job_002",
                    "status": "waiting_approval",
                    "short_reply": "I queued that task.",
                    "long_reply_text": "",
                    "long_reply_url": "",
                    "needs_followup": True,
                    "remote_request_id": "req_capture",
                }
            if payload["intent"] == "status_query":
                self.assertEqual(payload["remote_job_id"], "remote_job_002")
                return {
                    "ok": True,
                    "owner_id": "owner_you",
                    "remote_job_id": "remote_job_002",
                    "status": "running",
                    "short_reply": "The latest task is still running.",
                    "long_reply_text": "",
                    "long_reply_url": "",
                    "needs_followup": False,
                    "remote_request_id": "req_status",
                }
            if "通过" in transcript:
                self.assertEqual(payload["remote_job_id"], "remote_job_002")
                return {
                    "ok": True,
                    "owner_id": "owner_you",
                    "remote_job_id": "remote_job_002",
                    "status": "done",
                    "short_reply": "Approved. I pushed it forward.",
                    "long_reply_text": "",
                    "long_reply_url": "",
                    "needs_followup": False,
                    "remote_request_id": "req_approve",
                }
            raise AssertionError(f"Unexpected payload: {payload}")

        base_url = self._start_main_brain_server(responder)
        self._rebuild_services(
            {
                "main_brain": {
                    "enabled": True,
                    "base_url": base_url,
                    "owner_id": "owner_you",
                    "telegram_chat_id": "tg-123",
                    "timeout_seconds": 2,
                }
            }
        )
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "记一下，整理今天的项目进度。"
        created = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=88,
        )
        finished_create = self._wait_for_voice_turn_record(created.id)
        self.assertEqual(finished_create.remote_job_id, "remote_job_002")
        self.assertTrue(finished_create.needs_followup)

        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "刚才那个任务做到哪了？"
        status_turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=75,
        )
        finished_status = self._wait_for_voice_turn_record(status_turn.id)
        self.assertEqual(finished_status.intent, "status_query")
        self.assertEqual(finished_status.remote_job_id, "remote_job_002")
        self.assertEqual(finished_status.linked_job_id, "remote_job_002")
        self.assertEqual(finished_status.remote_status, "running")

        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "好，这个通过吧。"
        approve_turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=71,
        )
        finished_approve = self._wait_for_voice_turn_record(approve_turn.id)
        self.assertEqual(finished_approve.intent, "approval_action")
        self.assertEqual(finished_approve.remote_job_id, "remote_job_002")
        self.assertEqual(finished_approve.remote_status, "done")
        self.assertEqual(finished_approve.linked_job_id, "remote_job_002")

    def test_voice_turn_capture_task_queues_handoff_when_main_brain_unavailable(self) -> None:
        self._rebuild_services(
            {
                "main_brain": {
                    "enabled": True,
                    "base_url": "http://127.0.0.1:9",
                    "owner_id": "owner_you",
                    "telegram_chat_id": "tg-123",
                    "timeout_seconds": 1,
                }
            }
        )
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "记一下，等会同步一下今天的会议纪要。"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=67,
        )
        finished = self._wait_for_voice_turn_record(turn.id)

        self.assertTrue(finished.handoff_queued)
        self.assertIn("sync it to Telegram", finished.reply_text)
        handoffs = self.services.voice_turns.store.list("remote_handoffs")
        self.assertEqual(len(handoffs), 1)
        self.assertEqual(handoffs[0]["intent"], "capture_task")

    def test_voice_turn_status_query_degrades_when_main_brain_unavailable(self) -> None:
        self._rebuild_services(
            {
                "main_brain": {
                    "enabled": True,
                    "base_url": "http://127.0.0.1:9",
                    "owner_id": "owner_you",
                    "telegram_chat_id": "tg-123",
                    "timeout_seconds": 1,
                }
            }
        )
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "刚才那个任务做到哪了？"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=63,
        )
        finished = self._wait_for_voice_turn_record(turn.id)

        self.assertEqual(finished.intent, "status_query")
        self.assertFalse(finished.handoff_queued)
        self.assertIn("latest Telegram status", finished.reply_text)

    def test_voice_turn_approval_action_does_not_fake_success_when_main_brain_unavailable(self) -> None:
        local_waiting = self.services.orchestrator.submit_job(
            workflow="drafting_assistant",
            content="Please draft and send the customer summary.",
            source_channel="companion_remote",
            metadata={
                "device_id": "stick-s3-01",
                "session_id": "pet-session",
                "requested_actions": ["external_send"],
            },
        )
        self.assertEqual(local_waiting.status, "waiting_approval")

        self._rebuild_services(
            {
                "main_brain": {
                    "enabled": True,
                    "base_url": "http://127.0.0.1:9",
                    "owner_id": "owner_you",
                    "telegram_chat_id": "tg-123",
                    "timeout_seconds": 1,
                }
            }
        )
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "好，这个通过吧。"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=60,
        )
        finished = self._wait_for_voice_turn_record(turn.id)

        self.assertEqual(finished.intent, "approval_action")
        self.assertIn("have not approved or rejected", finished.reply_text)
        still_waiting = self.services.orchestrator.get_job(local_waiting.id)
        self.assertEqual(still_waiting.status, "waiting_approval")

    def test_voice_turn_remote_long_result_is_summarized_for_device(self) -> None:
        base_url = self._start_main_brain_server(
            lambda payload: {
                "ok": True,
                "owner_id": "owner_you",
                "remote_job_id": "remote_job_003",
                "status": "running",
                "short_reply": "",
                "long_reply_text": (
                    "The task is still running and has already produced a long planning artifact with multiple "
                    "sections, open questions, and a full execution trace that is better reviewed in Telegram."
                ),
                "long_reply_url": "",
                "needs_followup": True,
                "remote_request_id": "req_long",
            }
        )
        self._rebuild_services(
            {
                "main_brain": {
                    "enabled": True,
                    "base_url": base_url,
                    "owner_id": "owner_you",
                    "telegram_chat_id": "tg-123",
                }
            }
        )
        self.services.voice_turns.speech.transcribe = lambda *_args, **_kwargs: "刚才那个任务做到哪了？"
        self.services.voice_turns.speech.synthesize = lambda text: (self._make_test_wav(duration_seconds=0.5), "audio/wav")

        turn = self.services.voice_turns.create_turn_from_upload(
            device_id="stick-s3-01",
            session_id="pet-session",
            audio_bytes=self._make_test_wav(duration_seconds=0.8),
            battery_level=72,
        )
        finished = self._wait_for_voice_turn_record(turn.id)

        self.assertEqual(finished.remote_job_id, "remote_job_003")
        self.assertTrue(finished.needs_followup)
        self.assertIn("Check Telegram for the full details.", finished.reply_text)
        self.assertLessEqual(len(finished.display_text), 42)

    def test_restart_persists_jobs_and_conversations(self) -> None:
        self._post_json(
            "/api/messages/telegram",
            {
                "message_id": "tg-persist-001",
                "text": "我们把长期主机这件事推进一下。",
                "sender": "me",
                "telegram_chat_id": "tg-123",
                "owner_id": "owner_you",
            },
        )
        job = self.services.orchestrator.submit_job(
            workflow="inbox_capture",
            content="Persist this job across restart.",
            source_channel="telegram",
            metadata={"owner_id": "owner_you", "telegram_chat_id": "tg-123"},
        )
        _, rebuilt = build_services(str(self.config_path))
        self.assertIsNotNone(rebuilt.orchestrator.get_job(job.id))
        conversations = rebuilt.brain.store.list("conversations")
        self.assertTrue(conversations)
        self.assertTrue(any(item["channel"] == "telegram" for item in conversations))

    def test_json_state_imports_into_sqlite(self) -> None:
        import_dir = self.temp_dir / "import-case"
        import_dir.mkdir(parents=True, exist_ok=True)
        import_data_dir = import_dir / "data"
        import_data_dir.mkdir(parents=True, exist_ok=True)
        import_config_path = import_dir / "config.json"
        config = self._base_config()
        config["data_dir"] = str(import_data_dir)
        import_config_path.write_text(json.dumps(config), encoding="utf-8")
        legacy_state = {
            "jobs": {
                "job_legacy": {
                    "id": "job_legacy",
                    "workflow": "inbox_capture",
                    "status": "done",
                    "content": "Imported from legacy json.",
                    "source_channel": "telegram",
                    "metadata": {"owner_id": "owner_you"},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "result": {"summary": "legacy summary", "actions": [], "open_questions": [], "confidence": 0.8, "needs_approval": False, "structured_payload": {}},
                    "memory_candidate_ids": [],
                    "event_log": [],
                }
            },
            "memories": {},
            "memory_candidates": {},
            "skills": {},
            "messages": {},
            "device_events": {},
            "voice_turns": {},
            "companion_sessions": {},
            "audio_assets": {},
            "remote_handoffs": {},
            "conversations": {},
        }
        (import_data_dir / "state.json").write_text(json.dumps(legacy_state), encoding="utf-8")
        _, rebuilt = build_services(str(import_config_path))
        imported = rebuilt.orchestrator.get_job("job_legacy")
        self.assertEqual(imported.content, "Imported from legacy json.")
        self.assertTrue((import_data_dir / "state.db").exists())

    def _base_config(self) -> dict:
        return {
            "agent_name": "test-agent",
            "data_dir": str(self.temp_dir / "data"),
            "storage": {"backend": "sqlite"},
            "server": {"host": "127.0.0.1", "port": 8787},
            "model_router": {
                "primary": {
                    "provider": "openrouter",
                    "model": "mock-primary",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions",
                    "api_key_env": "MISSING_KEY",
                    "timeout_seconds": 1,
                },
                "auxiliary": {
                    "provider": "openrouter",
                    "model": "mock-aux",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions",
                    "api_key_env": "MISSING_KEY",
                    "timeout_seconds": 1,
                },
                "vision": {
                    "provider": "openrouter",
                    "model": "mock-vision",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions",
                    "api_key_env": "MISSING_KEY",
                    "timeout_seconds": 1,
                },
            },
            "wecom": {
                "token": "test-token",
                "encoding_aes_key": "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG",
                "corp_id": "ww1234567890abcd",
                "agent_id": "1000002",
            },
            "voice": {
                "api_key_env": "MISSING_KEY",
                "api_base_url": "https://openrouter.ai/api/v1",
                "transcription_model": "openai/gpt-audio",
                "transcription_language": "zh",
                "tts_model": "openai/gpt-4o-mini-tts-2025-12-15",
                "tts_voice": "alloy",
                "tts_instructions": "Speak warmly in concise Mandarin Chinese.",
                "audio_ttl_seconds": 2,
                "cleanup_interval_seconds": 60,
                "max_context_turns": 6,
            },
            "main_brain": {
                "enabled": False,
                "base_url": "",
                "owner_id": "owner_you",
                "telegram_chat_id": "tg-123",
                "timeout_seconds": 1,
            },
        }

    def _write_config(self, overrides: dict | None = None) -> None:
        config = self._base_config()
        self._deep_update(config, overrides or {})
        self.config_path.write_text(json.dumps(config), encoding="utf-8")

    def _rebuild_services(self, overrides: dict | None = None) -> None:
        self._write_config(overrides)
        _, self.services = build_services(str(self.config_path))

    def _deep_update(self, target: dict, overrides: dict) -> None:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def _start_main_brain_server(self, responder):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(inner_self) -> None:
                if inner_self.path != "/api/companion/intents":
                    inner_self.send_response(404)
                    inner_self.end_headers()
                    return
                length = int(inner_self.headers.get("Content-Length", "0"))
                payload = json.loads(inner_self.rfile.read(length).decode("utf-8"))
                response_payload = responder(payload)
                body = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
                inner_self.send_response(200)
                inner_self.send_header("Content-Type", "application/json; charset=utf-8")
                inner_self.send_header("Content-Length", str(len(body)))
                inner_self.end_headers()
                inner_self.wfile.write(body)

            def log_message(self, format: str, *args) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._main_brain_servers.append((server, thread))
        return f"http://127.0.0.1:{server.server_address[1]}"

    def _post_json(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def _wait_for_voice_turn(self, turn_id: str, timeout_seconds: float = 5.0) -> dict:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            with urllib.request.urlopen(f"{self.base_url}/api/companion/voice-turns/{turn_id}", timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload["status"] in {"done", "failed"}:
                return payload
            time.sleep(0.05)
        raise AssertionError(f"Voice turn {turn_id} did not finish in time.")

    def _wait_for_voice_turn_record(self, turn_id: str, timeout_seconds: float = 5.0):
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            turn = self.services.voice_turns.get_turn(turn_id)
            if turn.status in {"done", "failed"}:
                return turn
            time.sleep(0.05)
        raise AssertionError(f"Voice turn {turn_id} did not finish in time.")

    def _multipart_body(self, fields: dict[str, str], files: dict[str, dict]) -> dict[str, bytes | str]:
        boundary = f"----TestBoundary{int(time.time() * 1000)}"
        chunks: list[bytes] = []
        for key, value in fields.items():
            chunks.append(f"--{boundary}\r\n".encode("utf-8"))
            chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
            chunks.append(value.encode("utf-8"))
            chunks.append(b"\r\n")
        for key, file_item in files.items():
            chunks.append(f"--{boundary}\r\n".encode("utf-8"))
            chunks.append(
                (
                    f'Content-Disposition: form-data; name="{key}"; '
                    f'filename="{file_item["filename"]}"\r\n'
                ).encode("utf-8")
            )
            chunks.append(f'Content-Type: {file_item["content_type"]}\r\n\r\n'.encode("utf-8"))
            chunks.append(file_item["content"])
            chunks.append(b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
        return {
            "content_type": f"multipart/form-data; boundary={boundary}",
            "body": b"".join(chunks),
        }

    def _make_test_wav(self, duration_seconds: float) -> bytes:
        sample_rate = 16000
        total_frames = int(sample_rate * duration_seconds)
        with BytesIO() as buffer:
            with wave.open(buffer, "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate)
                handle.writeframes(b"\x00\x00" * total_frames)
            return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()

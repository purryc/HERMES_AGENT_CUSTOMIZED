from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import json

from hermes_personal_agent.brain import BrainService
from hermes_personal_agent.companion import CompanionService
from hermes_personal_agent.companion_intents import CompanionIntentService
from hermes_personal_agent.memory import MemoryManager
from hermes_personal_agent.messaging import MessagingGateway
from hermes_personal_agent.orchestrator import TaskOrchestrator
from hermes_personal_agent.skills import SkillRegistry
from hermes_personal_agent.voice_turns import VoiceTurnService, parse_multipart_form
from hermes_personal_agent.wecom import WeComCallbackError, WeComCallbackService


@dataclass
class AppServices:
    orchestrator: TaskOrchestrator
    messaging: MessagingGateway
    memory: MemoryManager
    skills: SkillRegistry
    brain: BrainService
    companion_intents: CompanionIntentService
    companion: CompanionService
    voice_turns: VoiceTurnService
    wecom: WeComCallbackService


def build_handler(services: AppServices):
    class RequestHandler(BaseHTTPRequestHandler):
        def _query(self) -> dict[str, str]:
            parsed = urlparse(self.path)
            return {key: values[0] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}

        def _body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0"))
            return self.rfile.read(length) if length else b""

        def _json(self) -> dict:
            raw = self._body() or b"{}"
            return json.loads(raw.decode("utf-8"))

        def _send(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, status: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._send(200, {"ok": True})
                return

            if parsed.path == "/api/wecom/callback":
                try:
                    reply = services.wecom.verify_url(self._query())
                    self._send_text(200, reply)
                except KeyError as exc:
                    self._send(400, {"error": f"Missing field: {exc}"})
                except WeComCallbackError as exc:
                    self._send(400, {"error": str(exc)})
                return

            if parsed.path == "/api/skills":
                skills = [skill.to_dict() for skill in services.skills.all()]
                self._send(200, {"skills": skills})
                return

            if parsed.path.startswith("/api/jobs/"):
                job_id = parsed.path.split("/")[-1]
                try:
                    job = services.orchestrator.get_job(job_id)
                    self._send(200, job.to_dict())
                except KeyError as exc:
                    self._send(404, {"error": str(exc)})
                return

            if parsed.path.startswith("/api/companion/voice-turns/"):
                turn_id = parsed.path.split("/")[-1]
                try:
                    turn = services.voice_turns.get_turn(turn_id)
                    self._send(200, services.voice_turns.serialize_turn(turn))
                except KeyError as exc:
                    self._send(404, {"error": str(exc)})
                return

            if parsed.path.startswith("/api/companion/audio/"):
                audio_asset_id = parsed.path.split("/")[-1]
                try:
                    asset = services.voice_turns.get_audio_asset(audio_asset_id)
                    self._send_bytes(200, asset.path.read_bytes(), asset.content_type)
                except KeyError as exc:
                    self._send(404, {"error": str(exc)})
                return

            self._send(404, {"error": "Not found"})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/wecom/callback":
                    raw_xml = self._body().decode("utf-8")
                    services.wecom.handle_callback(self._query(), raw_xml)
                    self._send_text(200, "")
                    return

                if parsed.path == "/api/companion/voice-turns":
                    content_type = self.headers.get("Content-Type", "")
                    fields, files = parse_multipart_form(content_type, self._body())
                    audio = files.get("audio")
                    if not audio:
                        raise ValueError("Missing audio field.")
                    device_id = fields.get("device_id", "m5stick-s3")
                    session_id = fields.get("session_id", "default-session")
                    battery_value = fields.get("battery_level")
                    battery_level = float(battery_value) if battery_value not in {None, ""} else None
                    turn = services.voice_turns.create_turn_from_upload(
                        device_id=device_id,
                        session_id=session_id,
                        audio_bytes=audio["content"],
                        battery_level=battery_level,
                        filename=audio["filename"],
                    )
                    self._send(201, services.voice_turns.serialize_turn(turn))
                    return

                payload = self._json()
                if parsed.path == "/api/jobs":
                    job = services.orchestrator.submit_job(
                        workflow=payload["workflow"],
                        content=payload["content"],
                        source_channel=payload.get("source_channel", "api"),
                        metadata=payload.get("metadata", {}),
                    )
                    self._send(201, job.to_dict())
                    return

                if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/approve"):
                    parts = parsed.path.strip("/").split("/")
                    job_id = parts[2]
                    decision = payload.get("decision", "approve")
                    if decision == "approve":
                        job = services.orchestrator.approve_job(job_id, payload.get("comment", ""))
                    else:
                        job = services.orchestrator.reject_job(job_id, payload.get("comment", ""))
                    self._send(200, job.to_dict())
                    return

                if parsed.path == "/api/messages/wechat":
                    result = services.messaging.ingest("wechat", payload)
                    self._send(200, result)
                    return

                if parsed.path == "/api/messages/wecom":
                    result = services.messaging.ingest("wecom", payload)
                    self._send(200, result)
                    return

                if parsed.path == "/api/messages/telegram":
                    result = services.brain.handle_telegram_message(payload)
                    self._send(200, result)
                    return

                if parsed.path == "/api/companion/events":
                    result = services.companion.ingest_event(payload)
                    self._send(201, result)
                    return

                if parsed.path == "/api/companion/intents":
                    result = services.companion_intents.handle_intent(payload)
                    self._send(200, result)
                    return

                if parsed.path == "/api/companion/text-turns":
                    turn = services.voice_turns.create_turn_from_text(
                        device_id=payload.get("device_id", "m5stick-s3-pet-01"),
                        session_id=payload.get("session_id", "main-session"),
                        text=payload.get("text", ""),
                        attachments=payload.get("attachments", []),
                    )
                    status = 201 if turn.status != "failed" else 500
                    self._send(status, services.voice_turns.serialize_turn(turn))
                    return

                if parsed.path.startswith("/api/memory-candidates/") and parsed.path.endswith("/confirm"):
                    candidate_id = parsed.path.strip("/").split("/")[2]
                    memory = services.memory.confirm_candidate(candidate_id)
                    self._send(200, memory.to_dict())
                    return

                self._send(404, {"error": "Not found"})
            except KeyError as exc:
                self._send(400, {"error": f"Missing field: {exc}"})
            except WeComCallbackError as exc:
                self._send(400, {"error": str(exc)})
            except ValueError as exc:
                self._send(400, {"error": str(exc)})
            except Exception as exc:
                self._send(500, {"error": str(exc)})

        def log_message(self, format: str, *args) -> None:
            return

    return RequestHandler


def serve(host: str, port: int, services: AppServices) -> None:
    server = ThreadingHTTPServer((host, port), build_handler(services))
    print(f"Hermes Personal Work Agent listening on http://{host}:{port}")
    server.serve_forever()

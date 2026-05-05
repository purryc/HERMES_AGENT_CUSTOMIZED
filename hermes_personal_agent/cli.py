from __future__ import annotations

import argparse
import json

from hermes_personal_agent.brain import BrainService
from hermes_personal_agent.companion import CompanionService
from hermes_personal_agent.companion_client import CompanionClient
from hermes_personal_agent.companion_intents import CompanionIntentService
from hermes_personal_agent.config import AgentConfig
from hermes_personal_agent.main_brain import MainBrainAdapter
from hermes_personal_agent.memory import MemoryManager
from hermes_personal_agent.messaging import MessagingGateway
from hermes_personal_agent.openrouter import ModelRouterAdapter
from hermes_personal_agent.orchestrator import TaskOrchestrator
from hermes_personal_agent.server import AppServices, serve
from hermes_personal_agent.skills import SkillRegistry
from hermes_personal_agent.storage import JsonStateStore, SQLiteStateStore
from hermes_personal_agent.voice_turns import VoiceTurnService
from hermes_personal_agent.wecom import WeComCallbackService


def build_services(config_path: str) -> tuple[AgentConfig, AppServices]:
    config = AgentConfig.load(config_path)
    storage_backend = str(config.raw.get("storage", {}).get("backend", "sqlite")).strip().lower()
    if storage_backend == "json":
        store = JsonStateStore(config.data_dir)
    else:
        store = SQLiteStateStore(config.data_dir)
    skills = SkillRegistry(store)
    memory = MemoryManager(store)
    models = ModelRouterAdapter(
        primary=config.model_profile("primary"),
        auxiliary=config.model_profile("auxiliary"),
        vision=config.model_profile("vision"),
    )
    orchestrator = TaskOrchestrator(store=store, models=models, memory=memory, skills=skills)
    brain = BrainService(
        store=store,
        models=models,
        orchestrator=orchestrator,
        memory=memory,
        default_owner_id=config.main_brain.owner_id or "local_owner",
    )
    messaging = MessagingGateway(store=store, orchestrator=orchestrator)
    companion_intents = CompanionIntentService(store=store, orchestrator=orchestrator)
    companion = CompanionService(store=store, orchestrator=orchestrator)
    main_brain = MainBrainAdapter(config.main_brain)
    voice_turns = VoiceTurnService(
        store=store,
        models=models,
        orchestrator=orchestrator,
        brain=brain,
        companion_intents=companion_intents,
        main_brain=main_brain,
        config=config.voice_runtime,
        data_dir=config.data_dir,
    )
    wecom = WeComCallbackService(config=config.wecom_callback, messaging=messaging)
    services = AppServices(
        orchestrator=orchestrator,
        messaging=messaging,
        memory=memory,
        skills=skills,
        brain=brain,
        companion_intents=companion_intents,
        companion=companion,
        voice_turns=voice_turns,
        wecom=wecom,
    )
    return config, services


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes personal work agent starter.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Run the HTTP API server.")
    serve_parser.add_argument("--config", required=True)
    serve_parser.add_argument("--host", default=None)
    serve_parser.add_argument("--port", type=int, default=None)

    submit_parser = subparsers.add_parser("submit", help="Submit a workflow job from CLI.")
    submit_parser.add_argument("--config", required=True)
    submit_parser.add_argument("--workflow", required=True)
    submit_parser.add_argument("--content", required=True)
    submit_parser.add_argument("--source-channel", default="terminal")
    submit_parser.add_argument("--metadata", default="{}")

    status_parser = subparsers.add_parser("status", help="Show a job status.")
    status_parser.add_argument("--config", required=True)
    status_parser.add_argument("--job-id", required=True)

    companion_send_parser = subparsers.add_parser("companion-send", help="Send a companion event.")
    companion_send_parser.add_argument("--api-base-url", required=True)
    companion_send_parser.add_argument("--queue-path", required=True)
    companion_send_parser.add_argument("--device-id", required=True)
    companion_send_parser.add_argument("--event-type", required=True)
    companion_send_parser.add_argument("--text", default="")

    companion_flush_parser = subparsers.add_parser("companion-flush", help="Flush queued companion events.")
    companion_flush_parser.add_argument("--api-base-url", required=True)
    companion_flush_parser.add_argument("--queue-path", required=True)

    args = parser.parse_args()
    config = None
    services = None
    if args.command in {"serve", "submit", "status"}:
        config, services = build_services(args.config)

    if args.command == "serve":
        assert config is not None and services is not None
        host = args.host or config.server_host
        port = args.port or config.server_port
        serve(host, port, services)
        return

    if args.command == "submit":
        assert services is not None
        metadata = json.loads(args.metadata)
        job = services.orchestrator.submit_job(
            workflow=args.workflow,
            content=args.content,
            source_channel=args.source_channel,
            metadata=metadata,
        )
        print(json.dumps(job.to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "status":
        assert services is not None
        job = services.orchestrator.get_job(args.job_id)
        print(services.orchestrator.format_status(job))
        return

    if args.command == "companion-send":
        client = CompanionClient(args.api_base_url, args.queue_path)
        result = client.send_event(
            {
                "device_id": args.device_id,
                "event_type": args.event_type,
                "text": args.text,
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "companion-flush":
        client = CompanionClient(args.api_base_url, args.queue_path)
        print(json.dumps(client.flush(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import urllib.error
import urllib.request


class CompanionClient:
    def __init__(self, api_base_url: str, queue_path: str) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)

    def send_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._post(payload)
            return {
                "queued": False,
                "response": response,
            }
        except (urllib.error.URLError, TimeoutError):
            self._append_to_queue(payload)
            return {
                "queued": True,
                "response": None,
            }

    def flush(self) -> dict[str, Any]:
        queued = self._load_queue()
        if not queued:
            return {"flushed": 0, "remaining": 0}

        remaining = []
        flushed = 0
        for item in queued:
            try:
                self._post(item)
                flushed += 1
            except (urllib.error.URLError, TimeoutError):
                remaining.append(item)
        self._write_queue(remaining)
        return {"flushed": flushed, "remaining": len(remaining)}

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.api_base_url}/api/companion/events",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def _append_to_queue(self, payload: dict[str, Any]) -> None:
        queued = self._load_queue()
        queued.append(payload)
        self._write_queue(queued)

    def _load_queue(self) -> list[dict[str, Any]]:
        if not self.queue_path.exists():
            return []
        with self.queue_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_queue(self, queued: list[dict[str, Any]]) -> None:
        with self.queue_path.open("w", encoding="utf-8") as handle:
            json.dump(queued, handle, ensure_ascii=False, indent=2)

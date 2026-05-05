from __future__ import annotations

from pathlib import Path
import json
import sqlite3
import threading


class JsonStateStore:
    DEFAULT_STATE = {
        "jobs": {},
        "memory_candidates": {},
        "memories": {},
        "skills": {},
        "messages": {},
        "device_events": {},
        "voice_turns": {},
        "companion_sessions": {},
        "audio_assets": {},
        "remote_handoffs": {},
        "conversations": {},
    }

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "state.json"
        self._lock = threading.RLock()
        self._state = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return json.loads(json.dumps(self.DEFAULT_STATE))
        with self.path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        state = json.loads(json.dumps(self.DEFAULT_STATE))
        state.update(raw)
        for collection in self.DEFAULT_STATE:
            state.setdefault(collection, {})
        return state

    def _save(self) -> None:
        temp_path = self.path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(self._state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        temp_path.replace(self.path)

    def upsert(self, collection: str, item_id: str, payload: dict) -> None:
        with self._lock:
            self._state.setdefault(collection, {})
            self._state[collection][item_id] = payload
            self._save()

    def get(self, collection: str, item_id: str) -> dict | None:
        with self._lock:
            item = self._state.setdefault(collection, {}).get(item_id)
            if item is None:
                return None
            return json.loads(json.dumps(item))

    def list(self, collection: str) -> list[dict]:
        with self._lock:
            values = list(self._state.setdefault(collection, {}).values())
            return json.loads(json.dumps(values))

    def exists(self, collection: str, item_id: str) -> bool:
        with self._lock:
            return item_id in self._state.setdefault(collection, {})

    def delete(self, collection: str, item_id: str) -> None:
        with self._lock:
            bucket = self._state.setdefault(collection, {})
            if item_id in bucket:
                del bucket[item_id]
                self._save()


class SQLiteStateStore:
    COLLECTIONS = (
        "jobs",
        "memory_candidates",
        "memories",
        "skills",
        "messages",
        "device_events",
        "voice_turns",
        "companion_sessions",
        "audio_assets",
        "remote_handoffs",
        "conversations",
    )

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "state.db"
        self.json_import_path = self.data_dir / "state.json"
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize()
        self._import_json_if_needed()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    collection TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (collection, item_id)
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_records_collection ON records(collection)"
            )
            self._connection.commit()

    def _import_json_if_needed(self) -> None:
        if not self.json_import_path.exists():
            return
        with self._lock:
            row = self._connection.execute("SELECT COUNT(*) AS count FROM records").fetchone()
            if row is not None and int(row["count"]) > 0:
                return
            with self.json_import_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            for collection in self.COLLECTIONS:
                bucket = raw.get(collection, {})
                if not isinstance(bucket, dict):
                    continue
                for item_id, payload in bucket.items():
                    self._connection.execute(
                        """
                        INSERT OR REPLACE INTO records(collection, item_id, payload)
                        VALUES (?, ?, ?)
                        """,
                        (collection, item_id, json.dumps(payload, ensure_ascii=False)),
                    )
            self._connection.commit()

    def upsert(self, collection: str, item_id: str, payload: dict) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO records(collection, item_id, payload)
                VALUES (?, ?, ?)
                """,
                (collection, item_id, json.dumps(payload, ensure_ascii=False)),
            )
            self._connection.commit()

    def get(self, collection: str, item_id: str) -> dict | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM records WHERE collection = ? AND item_id = ?",
                (collection, item_id),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["payload"])

    def list(self, collection: str) -> list[dict]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT payload FROM records WHERE collection = ?",
                (collection,),
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def exists(self, collection: str, item_id: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM records WHERE collection = ? AND item_id = ?",
                (collection, item_id),
            ).fetchone()
        return row is not None

    def delete(self, collection: str, item_id: str) -> None:
        with self._lock:
            self._connection.execute(
                "DELETE FROM records WHERE collection = ? AND item_id = ?",
                (collection, item_id),
            )
            self._connection.commit()

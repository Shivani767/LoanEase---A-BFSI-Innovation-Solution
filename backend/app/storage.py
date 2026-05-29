from __future__ import annotations

import json
from pathlib import Path
from threading import Lock


class ApplicationStore:
    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self.store_path.write_text("", encoding="utf-8")
        self._lock = Lock()

    def save(self, record: dict) -> None:
        line = json.dumps(record)
        with self._lock:
            with self.store_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def get(self, application_id: str) -> dict | None:
        with self._lock:
            if not self.store_path.exists():
                return None
            with self.store_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        continue
                    if record.get("application_id") == application_id:
                        return record
        return None

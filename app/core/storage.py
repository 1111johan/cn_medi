from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, List


class JsonListStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def read(self) -> List[Any]:
        with self.lock:
            raw = self.path.read_text(encoding="utf-8").strip()
            if not raw:
                return []
            return json.loads(raw)

    def write(self, data: List[Any]) -> None:
        with self.lock:
            tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(self.path)

    def append(self, item: Any) -> None:
        with self.lock:
            raw = self.path.read_text(encoding="utf-8").strip()
            data = json.loads(raw) if raw else []
            data.append(item)
            tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(self.path)


class JsonlStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, item: Any) -> None:
        with self.lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def read(self) -> List[Any]:
        if not self.path.exists():
            return []
        with self.lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            records = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
            return records

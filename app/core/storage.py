from __future__ import annotations

import os
import json
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List

try:
    import fcntl
except ImportError:  # pragma: no cover - fallback for non-POSIX runtimes.
    fcntl = None


class _PathMutex:
    def __init__(self, path: Path):
        self.path = path
        self.thread_lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    @contextmanager
    def hold(self) -> Iterator[None]:
        with self.thread_lock:
            with self.path.open("a+", encoding="utf-8") as lock_handle:
                if fcntl is not None:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    if fcntl is not None:
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _write_text_atomic(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)


class JsonListStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mutex = _PathMutex(self.path.with_name(f"{self.path.name}.lock"))
        with self.mutex.hold():
            if not self.path.exists():
                _write_text_atomic(self.path, "[]")

    def read(self) -> List[Any]:
        with self.mutex.hold():
            if not self.path.exists():
                return []
            raw = self.path.read_text(encoding="utf-8").strip()
            if not raw:
                return []
            return json.loads(raw)

    def write(self, data: List[Any]) -> None:
        with self.mutex.hold():
            _write_text_atomic(self.path, json.dumps(data, ensure_ascii=False, indent=2))

    def append(self, item: Any) -> None:
        with self.mutex.hold():
            raw = self.path.read_text(encoding="utf-8").strip()
            data = json.loads(raw) if raw else []
            data.append(item)
            _write_text_atomic(self.path, json.dumps(data, ensure_ascii=False, indent=2))


class JsonlStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mutex = _PathMutex(self.path.with_name(f"{self.path.name}.lock"))
        with self.mutex.hold():
            self.path.touch(exist_ok=True)

    def append(self, item: Any) -> None:
        with self.mutex.hold():
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())

    def read(self) -> List[Any]:
        if not self.path.exists():
            return []
        with self.mutex.hold():
            lines = self.path.read_text(encoding="utf-8").splitlines()
            records = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
            return records

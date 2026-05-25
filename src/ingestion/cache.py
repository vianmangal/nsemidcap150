from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileCache:
    base_dir: Path
    ttl_seconds: int | None = None

    def path_for(self, key: str) -> Path:
        return self.base_dir / key

    def get_bytes(self, key: str) -> bytes | None:
        path = self.path_for(key)
        if not path.exists():
            return None
        if self.ttl_seconds is not None:
            age = time.time() - path.stat().st_mtime
            if age > self.ttl_seconds:
                return None
        return path.read_bytes()

    def write_bytes(self, key: str, data: bytes) -> Path:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

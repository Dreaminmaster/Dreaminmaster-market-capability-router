from __future__ import annotations

import json
import os
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any


class DataError(RuntimeError):
    pass


class DataRepository:
    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir).expanduser().resolve() if data_dir else None

    def _external_path(self, name: str) -> Path | None:
        candidates = []
        if self.data_dir:
            candidates.append(self.data_dir / name)
        env_dir = os.getenv("MCR_DATA_DIR")
        if env_dir:
            candidates.append(Path(env_dir).expanduser() / name)
        candidates.append(Path.cwd() / "data" / "seed" / name)
        for path in candidates:
            if path.exists():
                return path
        return None

    @lru_cache(maxsize=32)
    def load(self, name: str) -> Any:
        path = self._external_path(name)
        if path:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise DataError(f"Unable to read {path}: {exc}") from exc
        try:
            package_file = resources.files("mcr.resources.seed").joinpath(name)
            return json.loads(package_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DataError(f"Seed data not found: {name}") from exc

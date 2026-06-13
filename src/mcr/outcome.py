from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OutcomeStore:
    def __init__(self, path: str | Path = "outcomes.jsonl"):
        self.path = Path(path)

    def append(self, outcome: dict[str, Any]) -> None:
        safe = dict(outcome)
        forbidden = {"password", "verification_code", "payment_password", "id_number", "bank_card"}
        leaked = forbidden.intersection(k.lower() for k in safe.keys())
        if leaked:
            raise ValueError(f"Sensitive fields are not allowed: {sorted(leaked)}")
        safe.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(safe, ensure_ascii=False) + "\n")

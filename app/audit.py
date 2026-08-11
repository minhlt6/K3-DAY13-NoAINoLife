from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def log_audit_event(event_type: str, details: dict | None = None) -> None:
    """Log critical security and configuration events to AUDIT_LOG_PATH."""
    audit_path_str = os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl")
    audit_path = Path(audit_path_str)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "details": details or {},
    }

    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

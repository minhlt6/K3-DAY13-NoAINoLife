from __future__ import annotations

from .audit import log_audit_event

STATE = {
    "rag_slow": False,
    "tool_fail": False,
    "cost_spike": False,
}


def enable(name: str) -> None:
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    STATE[name] = True
    log_audit_event("incident_enabled", {"incident_name": name})


def disable(name: str) -> None:
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    STATE[name] = False
    log_audit_event("incident_disabled", {"incident_name": name})


def status() -> dict[str, bool]:
    return dict(STATE)

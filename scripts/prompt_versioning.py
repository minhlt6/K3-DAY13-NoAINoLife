from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from langfuse import get_client  # noqa: E402
from structlog.contextvars import bind_contextvars, clear_contextvars  # noqa: E402

from app.agent import LabAgent  # noqa: E402
from app.cli import configure_utf8_stdio  # noqa: E402


PROMPT_NAME = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")
EVIDENCE_PATH = REPO_ROOT / "submission" / "evidence" / "prompt-versioning.json"
PROMPT_V1 = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
PROMPT_V2 = (
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Instruction=Answer in at most three concise sentences using the supplied docs."
)


def client():
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        raise RuntimeError("Thiếu LANGFUSE_PUBLIC_KEY hoặc LANGFUSE_SECRET_KEY trong .env")
    return get_client()


def prompt_for_label(label: str) -> Any | None:
    try:
        return client().api.prompts.get(PROMPT_NAME, label=label)
    except Exception:
        return None


def prompt_status() -> dict[str, Any]:
    status: dict[str, Any] = {"prompt_name": PROMPT_NAME, "labels": {}}
    for label in ("baseline", "candidate", "production"):
        prompt = prompt_for_label(label)
        status["labels"][label] = None if prompt is None else int(prompt.version)
    return status


def append_evidence(action: str, details: dict[str, Any]) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if EVIDENCE_PATH.exists():
        try:
            payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"events": []}
    else:
        payload = {"events": []}
    payload.setdefault("events", []).append(
        {
            "ts": datetime.now(UTC).isoformat(),
            "action": action,
            **details,
        }
    )
    payload["current_status"] = prompt_status()
    EVIDENCE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def setup_prompts() -> None:
    baseline = prompt_for_label("baseline")
    candidate = prompt_for_label("candidate")
    created: list[dict[str, Any]] = []

    if baseline is None:
        baseline = client().create_prompt(
            name=PROMPT_NAME,
            prompt=PROMPT_V1,
            labels=["baseline", "production"],
            tags=["checkpoint-2", "baseline"],
            type="text",
            commit_message="Checkpoint 2 baseline prompt",
        )
        created.append({"label": "baseline", "version": int(baseline.version)})

    if candidate is None:
        candidate = client().create_prompt(
            name=PROMPT_NAME,
            prompt=PROMPT_V2,
            labels=["candidate"],
            tags=["checkpoint-2", "candidate"],
            type="text",
            commit_message="Checkpoint 2 concise candidate prompt",
        )
        created.append({"label": "candidate", "version": int(candidate.version)})

    client().flush()
    append_evidence("setup", {"created": created})
    print(json.dumps(prompt_status(), ensure_ascii=False, indent=2))


def move_production(label: str) -> None:
    prompt = prompt_for_label(label)
    if prompt is None:
        raise RuntimeError(f"Không tìm thấy prompt label '{label}'. Hãy chạy action setup trước.")
    before = prompt_status()
    labels = [label, "production"] if label != "production" else ["production"]
    client().update_prompt(name=PROMPT_NAME, version=int(prompt.version), new_labels=labels)
    client().flush()
    after = prompt_status()
    action = "rollback" if label == "baseline" else "promote"
    append_evidence(action, {"target_version": int(prompt.version), "before": before, "after": after})
    print(json.dumps({"action": action, "before": before, "after": after}, ensure_ascii=False, indent=2))


def create_trace(label: str) -> None:
    prompt = prompt_for_label(label)
    if prompt is None:
        raise RuntimeError(f"Không tìm thấy prompt label '{label}'. Hãy chạy action setup trước.")

    os.environ["LANGFUSE_PROMPT_LABEL"] = label
    trace_id = client().create_trace_id(seed=f"checkpoint-2-{label}-{uuid.uuid4().hex}")
    correlation_id = f"req-{uuid.uuid4().hex[:8]}"
    clear_contextvars()
    bind_contextvars(correlation_id=correlation_id)
    result = LabAgent().run(
        user_id="checkpoint-2",
        feature="qa",
        session_id=f"prompt-{label}",
        message="Explain why metrics, traces, and logs work together.",
        langfuse_trace_id=trace_id,
    )
    client().flush()
    details = {
        "label": label,
        "version": int(prompt.version),
        "trace_id": trace_id,
        "trace_url": client().get_trace_url(trace_id=trace_id),
        "correlation_id": correlation_id,
        "latency_ms": result.latency_ms,
    }
    append_evidence("trace", details)
    print(json.dumps(details, ensure_ascii=False, indent=2))


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Quản lý prompt evidence cho Checkpoint 2")
    parser.add_argument(
        "action",
        choices=["setup", "status", "trace", "promote", "rollback", "complete"],
    )
    parser.add_argument("--label", choices=["baseline", "candidate", "production"])
    args = parser.parse_args()

    try:
        if args.action == "setup":
            setup_prompts()
        elif args.action == "status":
            print(json.dumps(prompt_status(), ensure_ascii=False, indent=2))
        elif args.action == "trace":
            if args.label is None:
                parser.error("action trace yêu cầu --label")
            create_trace(args.label)
        elif args.action == "promote":
            move_production("candidate")
        elif args.action == "rollback":
            move_production("baseline")
        else:
            setup_prompts()
            create_trace("baseline")
            create_trace("candidate")
            move_production("candidate")
            create_trace("production")
            move_production("baseline")
            create_trace("production")
    except Exception as exc:
        print(f"LỖI: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

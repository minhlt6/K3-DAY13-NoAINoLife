from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"
AUDIT_PATH = EVIDENCE_DIR / "prompt-versioning.json"
FONT_REGULAR = Path(r"C:\Windows\Fonts\consola.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\consolab.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size=size)


def render_text_evidence(title: str, subtitle: str, lines: list[str], output: Path) -> None:
    width = 1500
    margin = 64
    title_font = font(36, bold=True)
    subtitle_font = font(20)
    body_font = font(24)
    line_height = 38
    height = max(500, margin * 2 + 90 + line_height * len(lines))

    image = Image.new("RGB", (width, height), "#0d1117")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (28, 28, width - 28, height - 28),
        radius=22,
        fill="#161b22",
        outline="#30363d",
        width=2,
    )
    draw.text((margin, margin), title, font=title_font, fill="#f0f6fc")
    draw.text((margin, margin + 52), subtitle, font=subtitle_font, fill="#8b949e")

    y = margin + 110
    for line in lines:
        color = "#3fb950" if line.startswith(("PASS", "OK", "+")) else "#c9d1d9"
        if line.startswith(("BEFORE", "AFTER", "TRACE")):
            color = "#58a6ff"
        draw.text((margin, y), line, font=body_font, fill=color)
        y += line_height

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def capture_validator() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_dashboard.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    stdout = completed.stdout.strip().splitlines()
    lines = [
        "> python scripts/validate_dashboard.py",
        "",
        *(stdout or ["(no stdout)"]),
        "",
        f"PASS exit_code={completed.returncode}" if completed.returncode == 0 else f"FAIL exit_code={completed.returncode}",
    ]
    render_text_evidence(
        "Dashboard contract validator",
        "Generated from the actual validator process; no secrets included.",
        lines,
        EVIDENCE_DIR / "03-dashboard-validator.png",
    )
    if completed.returncode != 0:
        raise RuntimeError("validate_dashboard.py failed")


def capture_prompt_evidence() -> None:
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    events = payload["events"]
    traces = [event for event in events if event["action"] == "trace"]
    baseline_trace = next(event for event in traces if event["label"] == "baseline")
    candidate_trace = next(event for event in traces if event["label"] == "candidate")
    production_traces = [event for event in traces if event["label"] == "production"]
    status = payload["current_status"]

    version_lines = [
        f"Prompt: {status['prompt_name']}",
        f"+ baseline  -> version {status['labels']['baseline']}",
        f"+ candidate -> version {status['labels']['candidate']}",
        f"+ production -> version {status['labels']['production']} (after rollback)",
        "",
        f"TRACE baseline/v1  {baseline_trace['trace_id']}",
        f"      correlation  {baseline_trace['correlation_id']}",
        f"TRACE candidate/v2 {candidate_trace['trace_id']}",
        f"      correlation  {candidate_trace['correlation_id']}",
    ]
    render_text_evidence(
        "Langfuse prompt versions and traces",
        "Generated from the real Langfuse API audit in prompt-versioning.json.",
        version_lines,
        EVIDENCE_DIR / "06-prompt-versions-api.png",
    )

    promote = next(event for event in events if event["action"] == "promote")
    rollback = next(event for event in events if event["action"] == "rollback")
    rollback_lines = [
        "PROMOTE production: v1 -> v2",
        f"BEFORE {json.dumps(promote['before']['labels'], sort_keys=True)}",
        f"AFTER  {json.dumps(promote['after']['labels'], sort_keys=True)}",
        "",
        "ROLLBACK production: v2 -> v1",
        f"BEFORE {json.dumps(rollback['before']['labels'], sort_keys=True)}",
        f"AFTER  {json.dumps(rollback['after']['labels'], sort_keys=True)}",
        "",
        f"TRACE production/v2 {production_traces[0]['trace_id']}",
        f"TRACE production/v1 {production_traces[-1]['trace_id']}",
        "+ Final state: production points to baseline version 1",
    ]
    render_text_evidence(
        "Langfuse production label rollback",
        "Generated from real before/after API responses; full audit JSON is committed beside this image.",
        rollback_lines,
        EVIDENCE_DIR / "07-prompt-rollback-api.png",
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    capture_validator()
    capture_prompt_evidence()
    print("Đã tạo evidence Checkpoint 2 trong submission/evidence/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

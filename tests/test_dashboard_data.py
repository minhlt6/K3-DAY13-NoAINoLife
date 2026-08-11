from __future__ import annotations

import json
from pathlib import Path

from app.dashboard_data import (
    build_error_breakdown,
    build_minute_series,
    build_summary,
    filter_time_window,
    load_log_dataframe,
)


def _write_records(path: Path) -> None:
    records = [
        {"ts": "2026-08-11T00:00:01Z", "event": "request_received"},
        {
            "ts": "2026-08-11T00:00:02Z",
            "event": "response_sent",
            "latency_ms": 100,
            "cost_usd": 0.10,
            "tokens_in": 10,
            "tokens_out": 20,
            "quality_score": 0.8,
        },
        {"ts": "2026-08-11T00:01:01Z", "event": "request_received"},
        {
            "ts": "2026-08-11T00:01:02Z",
            "event": "request_failed",
            "error_type": "TimeoutError",
        },
    ]
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\nnot-json\n",
        encoding="utf-8",
    )


def test_dashboard_aggregations_follow_the_contract(tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    _write_records(log_path)

    frame = load_log_dataframe(log_path)
    summary = build_summary(frame)
    minute_series = build_minute_series(frame)
    errors = build_error_breakdown(frame)

    assert len(frame) == 4
    assert summary["request_count"] == 2
    assert summary["error_count"] == 1
    assert summary["error_rate_pct"] == 50
    assert summary["latency_p95_ms"] == 100
    assert summary["total_cost_usd"] == 0.10
    assert summary["tokens_in_total"] == 10
    assert summary["tokens_out_total"] == 20
    assert summary["quality_avg"] == 0.8
    assert minute_series["requests"].tolist() == [1, 1]
    assert minute_series["error_rate_pct"].tolist() == [0, 100]
    assert errors.to_dict("records") == [{"error_type": "TimeoutError", "count": 1}]


def test_time_window_is_anchored_to_latest_event(tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    _write_records(log_path)
    frame = load_log_dataframe(log_path)

    filtered = filter_time_window(frame, minutes=1)

    assert len(filtered) == 3

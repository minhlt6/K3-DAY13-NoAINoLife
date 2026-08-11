from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


LOG_COLUMNS = (
    "ts",
    "event",
    "latency_ms",
    "cost_usd",
    "tokens_in",
    "tokens_out",
    "quality_score",
    "error_type",
)

MINUTE_COLUMNS = (
    "minute",
    "requests",
    "errors",
    "error_rate_pct",
    "latency_p50_ms",
    "latency_p95_ms",
    "latency_p99_ms",
    "cost_usd",
    "cost_cumulative_usd",
    "tokens_in",
    "tokens_out",
    "tokens_cumulative",
    "quality_score",
)


def load_log_dataframe(path: Path) -> pd.DataFrame:
    """Load valid JSON log records without failing on partial/corrupt lines."""
    if not path.exists():
        return pd.DataFrame(columns=LOG_COLUMNS)

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)

    if not records:
        return pd.DataFrame(columns=LOG_COLUMNS)

    frame = pd.json_normalize(records)
    for column in LOG_COLUMNS:
        if column not in frame:
            frame[column] = pd.NA
    frame["ts"] = pd.to_datetime(frame["ts"], errors="coerce", utc=True)
    return frame.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)


def filter_time_window(frame: pd.DataFrame, minutes: int | None = 60) -> pd.DataFrame:
    """Keep the requested window, anchored to the newest available event."""
    if frame.empty or minutes is None:
        return frame.copy()
    latest = frame["ts"].max()
    start = latest - pd.Timedelta(minutes=minutes)
    return frame.loc[frame["ts"] >= start].copy()


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").dropna()


def build_summary(frame: pd.DataFrame) -> dict[str, Any]:
    requests = frame.loc[frame["event"] == "request_received"]
    responses = frame.loc[frame["event"] == "response_sent"]
    failures = frame.loc[frame["event"] == "request_failed"]

    latency = _numeric(responses, "latency_ms")
    costs = _numeric(responses, "cost_usd")
    tokens_in = _numeric(responses, "tokens_in")
    tokens_out = _numeric(responses, "tokens_out")
    quality = _numeric(responses, "quality_score")

    minute_counts = requests.set_index("ts").resample("1min").size() if not requests.empty else pd.Series(dtype="float64")
    request_count = int(len(requests))
    error_count = int(len(failures))

    return {
        "request_count": request_count,
        "requests_per_minute": float(minute_counts.mean()) if not minute_counts.empty else 0.0,
        "error_count": error_count,
        "error_rate_pct": (error_count / request_count * 100) if request_count else 0.0,
        "latency_p50_ms": float(latency.quantile(0.50)) if not latency.empty else 0.0,
        "latency_p95_ms": float(latency.quantile(0.95)) if not latency.empty else 0.0,
        "latency_p99_ms": float(latency.quantile(0.99)) if not latency.empty else 0.0,
        "total_cost_usd": float(costs.sum()),
        "tokens_in_total": int(tokens_in.sum()),
        "tokens_out_total": int(tokens_out.sum()),
        "quality_avg": float(quality.mean()) if not quality.empty else 0.0,
        "latest_ts": frame["ts"].max() if not frame.empty else None,
    }


def build_minute_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the six dashboard signals into aligned one-minute buckets."""
    if frame.empty:
        return pd.DataFrame(columns=MINUTE_COLUMNS)

    working = frame.copy()
    working["minute"] = working["ts"].dt.floor("min")
    minutes = pd.DataFrame(
        {"minute": pd.date_range(working["minute"].min(), working["minute"].max(), freq="1min")}
    )

    requests = working.loc[working["event"] == "request_received"]
    failures = working.loc[working["event"] == "request_failed"]
    responses = working.loc[working["event"] == "response_sent"].copy()

    request_counts = requests.groupby("minute").size().rename("requests")
    error_counts = failures.groupby("minute").size().rename("errors")

    for column in ("latency_ms", "cost_usd", "tokens_in", "tokens_out", "quality_score"):
        responses[column] = pd.to_numeric(responses[column], errors="coerce")

    if responses.empty:
        response_metrics = pd.DataFrame(index=pd.DatetimeIndex([], name="minute"))
    else:
        grouped = responses.groupby("minute")
        response_metrics = pd.DataFrame(
            {
                "latency_p50_ms": grouped["latency_ms"].quantile(0.50),
                "latency_p95_ms": grouped["latency_ms"].quantile(0.95),
                "latency_p99_ms": grouped["latency_ms"].quantile(0.99),
                "cost_usd": grouped["cost_usd"].sum(),
                "tokens_in": grouped["tokens_in"].sum(),
                "tokens_out": grouped["tokens_out"].sum(),
                "quality_score": grouped["quality_score"].mean(),
            }
        )

    series = minutes.set_index("minute").join(request_counts).join(error_counts).join(response_metrics)
    for column in ("requests", "errors", "cost_usd", "tokens_in", "tokens_out"):
        series[column] = series[column].fillna(0)
    series["error_rate_pct"] = (
        series["errors"].div(series["requests"].where(series["requests"] > 0)).mul(100).fillna(0)
    )
    series["cost_cumulative_usd"] = series["cost_usd"].cumsum()
    series["tokens_cumulative"] = (series["tokens_in"] + series["tokens_out"]).cumsum()
    return series.reset_index().loc[:, MINUTE_COLUMNS]


def build_error_breakdown(frame: pd.DataFrame) -> pd.DataFrame:
    failures = frame.loc[frame["event"] == "request_failed"].copy()
    if failures.empty:
        return pd.DataFrame(columns=["error_type", "count"])
    failures["error_type"] = failures["error_type"].fillna("UnknownError")
    return failures.groupby("error_type").size().rename("count").reset_index()

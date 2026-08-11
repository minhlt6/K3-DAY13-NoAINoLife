from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from app.dashboard_data import (
    build_error_breakdown,
    build_minute_series,
    build_summary,
    filter_time_window,
    load_log_dataframe,
)


REPO_ROOT = Path(__file__).resolve().parent
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
REFRESH_SECONDS = 30
CHART_HEIGHT = 150

THRESHOLDS = {
    "latency_p95_ms": 3000.0,
    "requests_per_minute": 1.0,
    "error_rate_pct": 2.0,
    "total_cost_usd": 2.5,
    "tokens_total": 50_000,
    "quality_avg": 0.75,
}


st.set_page_config(
    page_title="Day 13 AI observability",
    page_icon=":material/monitoring:",
    layout="wide",
)


@st.cache_data(ttl=5, max_entries=4, show_spinner=False)
def load_logs(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns  # Cache key only; invalidates immediately when the file changes.
    return load_log_dataframe(Path(path))


def status_label(value: float, threshold: float, operator: str) -> str:
    passed = value <= threshold if operator == "lte" else value >= threshold
    return "Đạt SLO" if passed else "Vi phạm SLO"


def line_with_threshold(
    frame: pd.DataFrame,
    *,
    value_columns: list[str],
    labels: list[str],
    threshold: float,
    y_title: str,
) -> alt.LayerChart:
    chart_data = frame.loc[:, ["minute", *value_columns]].melt(
        id_vars="minute",
        value_vars=value_columns,
        var_name="series",
        value_name="value",
    )
    chart_data["series"] = chart_data["series"].map(dict(zip(value_columns, labels, strict=True)))

    lines = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("minute:T", title="Thời gian"),
            y=alt.Y("value:Q", title=y_title),
            color=alt.Color("series:N", title=None, legend=alt.Legend(orient="bottom")),
            tooltip=[
                alt.Tooltip("minute:T", title="Thời gian", format="%H:%M"),
                alt.Tooltip("series:N", title="Chỉ số"),
                alt.Tooltip("value:Q", title="Giá trị", format=",.3f"),
            ],
        )
    )
    rule_data = pd.DataFrame({"threshold": [threshold]})
    rule = (
        alt.Chart(rule_data)
        .mark_rule(color="#ef4444", strokeDash=[6, 4], strokeWidth=2)
        .encode(y="threshold:Q")
    )
    return (lines + rule).properties(height=CHART_HEIGHT)


def render_chart(
    series: pd.DataFrame,
    *,
    value_columns: list[str],
    labels: list[str],
    threshold: float,
    y_title: str,
    key: str,
) -> None:
    if series.empty:
        st.info("Chưa có dữ liệu trong khoảng thời gian đã chọn.")
        return
    st.altair_chart(
        line_with_threshold(
            series,
            value_columns=value_columns,
            labels=labels,
            threshold=threshold,
            y_title=y_title,
        ),
        width="stretch",
        key=key,
    )


def render_latency(summary: dict, series: pd.DataFrame) -> None:
    threshold = THRESHOLDS["latency_p95_ms"]
    with st.container(border=True):
        st.subheader("Latency percentiles")
        st.caption(
            f"Đơn vị: ms · SLO P95 ≤ {threshold:,.0f} ms · "
            f"{status_label(summary['latency_p95_ms'], threshold, 'lte')}"
        )
        with st.container(horizontal=True):
            st.metric("P50", f"{summary['latency_p50_ms']:,.0f}")
            st.metric("P95", f"{summary['latency_p95_ms']:,.0f}")
            st.metric("P99", f"{summary['latency_p99_ms']:,.0f}")
        render_chart(
            series,
            value_columns=["latency_p50_ms", "latency_p95_ms", "latency_p99_ms"],
            labels=["P50", "P95", "P99"],
            threshold=threshold,
            y_title="Latency (ms)",
            key="latency_chart",
        )


def render_traffic(summary: dict, series: pd.DataFrame) -> None:
    threshold = THRESHOLDS["requests_per_minute"]
    with st.container(border=True):
        st.subheader("Request traffic")
        st.caption(
            f"Đơn vị: requests/phút · Threshold ≥ {threshold:,.0f} · "
            f"{status_label(summary['requests_per_minute'], threshold, 'gte')}"
        )
        with st.container(horizontal=True):
            st.metric("Tổng requests", f"{summary['request_count']:,}")
            st.metric("Trung bình/phút", f"{summary['requests_per_minute']:.1f}")
        render_chart(
            series,
            value_columns=["requests"],
            labels=["Requests/phút"],
            threshold=threshold,
            y_title="Requests/phút",
            key="traffic_chart",
        )


def render_errors(summary: dict, series: pd.DataFrame, errors: pd.DataFrame) -> None:
    threshold = THRESHOLDS["error_rate_pct"]
    with st.container(border=True):
        st.subheader("Error rate and breakdown")
        st.caption(
            f"Đơn vị: % · SLO error rate ≤ {threshold:.1f}% · "
            f"{status_label(summary['error_rate_pct'], threshold, 'lte')}"
        )
        with st.container(horizontal=True):
            st.metric("Error rate", f"{summary['error_rate_pct']:.2f}%")
            st.metric("Lỗi", f"{summary['error_count']:,}")
        render_chart(
            series,
            value_columns=["error_rate_pct"],
            labels=["Error rate"],
            threshold=threshold,
            y_title="Error rate (%)",
            key="errors_chart",
        )
        if errors.empty:
            st.caption("Breakdown: không có lỗi trong cửa sổ hiện tại.")
        else:
            breakdown = ", ".join(
                f"{row.error_type}: {row.count}" for row in errors.itertuples(index=False)
            )
            st.caption(f"Breakdown: {breakdown}")


def render_cost(summary: dict, series: pd.DataFrame) -> None:
    threshold = THRESHOLDS["total_cost_usd"]
    with st.container(border=True):
        st.subheader("Cost over time")
        st.caption(
            f"Đơn vị: USD · Budget cửa sổ ≤ ${threshold:.2f} · "
            f"{status_label(summary['total_cost_usd'], threshold, 'lte')}"
        )
        st.metric("Tổng chi phí", f"${summary['total_cost_usd']:.4f}")
        render_chart(
            series,
            value_columns=["cost_cumulative_usd"],
            labels=["Chi phí tích lũy"],
            threshold=threshold,
            y_title="USD",
            key="cost_chart",
        )


def render_tokens(summary: dict, series: pd.DataFrame) -> None:
    threshold = THRESHOLDS["tokens_total"]
    total = summary["tokens_in_total"] + summary["tokens_out_total"]
    with st.container(border=True):
        st.subheader("Input and output tokens")
        st.caption(
            f"Đơn vị: tokens · Threshold tổng ≤ {threshold:,.0f} · "
            f"{status_label(total, threshold, 'lte')}"
        )
        with st.container(horizontal=True):
            st.metric("Input", f"{summary['tokens_in_total']:,}")
            st.metric("Output", f"{summary['tokens_out_total']:,}")
        render_chart(
            series,
            value_columns=["tokens_cumulative"],
            labels=["Tổng token tích lũy"],
            threshold=threshold,
            y_title="Tokens",
            key="tokens_chart",
        )


def render_quality(summary: dict, series: pd.DataFrame) -> None:
    threshold = THRESHOLDS["quality_avg"]
    with st.container(border=True):
        st.subheader("Quality proxy")
        st.caption(
            f"Đơn vị: score 0–1 · SLO trung bình ≥ {threshold:.2f} · "
            f"{status_label(summary['quality_avg'], threshold, 'gte')}"
        )
        st.metric("Quality trung bình", f"{summary['quality_avg']:.3f}")
        render_chart(
            series,
            value_columns=["quality_score"],
            labels=["Quality trung bình"],
            threshold=threshold,
            y_title="Score (0–1)",
            key="quality_chart",
        )


@st.fragment(run_every=REFRESH_SECONDS)
def render_dashboard(window_minutes: int | None) -> None:
    modified_ns = LOG_PATH.stat().st_mtime_ns if LOG_PATH.exists() else 0
    frame = load_logs(str(LOG_PATH), modified_ns)
    filtered = filter_time_window(frame, window_minutes)
    summary = build_summary(filtered)
    series = build_minute_series(filtered)
    errors = build_error_breakdown(filtered)

    latest = summary["latest_ts"]
    if latest is None:
        st.warning("Chưa có log. Hãy chạy API và `python scripts/load_test.py --concurrency 5`.")
    else:
        st.caption(
            f"Bản ghi mới nhất: {latest.strftime('%Y-%m-%d %H:%M:%S UTC')} · "
            f"{len(filtered):,} log records · tự refresh mỗi {REFRESH_SECONDS} giây"
        )

    first_row = st.columns(3, gap="medium")
    with first_row[0]:
        render_latency(summary, series)
    with first_row[1]:
        render_traffic(summary, series)
    with first_row[2]:
        render_errors(summary, series, errors)

    second_row = st.columns(3, gap="medium")
    with second_row[0]:
        render_cost(summary, series)
    with second_row[1]:
        render_tokens(summary, series)
    with second_row[2]:
        render_quality(summary, series)


st.title(":material/monitoring: Day 13 AI observability")
st.caption("Nguồn chuẩn: data/logs.jsonl · 6 panel theo config/dashboard.yaml")

with st.sidebar:
    st.header("Bộ lọc")
    selected_window = st.segmented_control(
        "Khoảng thời gian",
        options=["60 phút", "4 giờ", "Tất cả"],
        default="60 phút",
    )
    st.caption("Mặc định 60 phút · auto-refresh 30 giây")

window_map = {"60 phút": 60, "4 giờ": 240, "Tất cả": None}
render_dashboard(window_map[selected_window or "60 phút"])

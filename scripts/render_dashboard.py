import json
import math
import os
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
OUTPUT_HTML = REPO_ROOT / "submission" / "evidence" / "dashboard.html"

def percentile(values, p):
    if not values:
        return 0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    d0 = s[int(f)] * (c - k)
    d1 = s[int(c)] * (k - f)
    return float(d0 + d1)

def parse_logs():
    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} not found.")
        sys.exit(1)

    lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines:
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    # Group by 1-minute buckets
    buckets = {}
    total_received = 0
    total_failed = 0
    total_cost = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    all_latencies = []
    all_qualities = []
    error_types = {}

    for r in records:
        ts_str = r.get("ts")
        event = r.get("event")
        
        # parse timestamp
        minute_key = "00:00"
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                minute_key = dt.strftime("%H:%M")
            except Exception:
                pass
        
        if minute_key not in buckets:
            buckets[minute_key] = {
                "latencies": [],
                "received": 0,
                "failed": 0,
                "cost": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
                "qualities": []
            }
        
        b = buckets[minute_key]
        if event == "request_received":
            b["received"] += 1
            total_received += 1
        elif event == "request_failed":
            b["failed"] += 1
            total_failed += 1
            err = r.get("error_type", "UnknownError")
            error_types[err] = error_types.get(err, 0) + 1
        elif event == "response_sent":
            lat = r.get("latency_ms", 0)
            b["latencies"].append(lat)
            all_latencies.append(lat)
            
            c = r.get("cost_usd", 0.0)
            b["cost"] += c
            total_cost += c
            
            t_in = r.get("tokens_in", 0)
            t_out = r.get("tokens_out", 0)
            b["tokens_in"] += t_in
            b["tokens_out"] += t_out
            total_tokens_in += t_in
            total_tokens_out += t_out
            
            q = r.get("quality_score")
            if q is not None:
                b["qualities"].append(q)
                all_qualities.append(q)

    # Sort minutes
    sorted_minutes = sorted(buckets.keys())
    
    p50_list = []
    p95_list = []
    p99_list = []
    traffic_list = []
    error_rate_list = []
    cost_list = []
    tokens_in_list = []
    tokens_out_list = []
    quality_list = []

    for m in sorted_minutes:
        b = buckets[m]
        lats = b["latencies"]
        p50_list.append(round(percentile(lats, 50), 1))
        p95_list.append(round(percentile(lats, 95), 1))
        p99_list.append(round(percentile(lats, 99), 1))
        
        traffic_list.append(b["received"])
        
        rec = b["received"] + b["failed"]
        err_pct = (b["failed"] / rec * 100.0) if rec > 0 else 0.0
        error_rate_list.append(round(err_pct, 2))
        
        cost_list.append(round(b["cost"], 5))
        tokens_in_list.append(b["tokens_in"])
        tokens_out_list.append(b["tokens_out"])
        
        q_avg = sum(b["qualities"]) / len(b["qualities"]) if b["qualities"] else 0.0
        quality_list.append(round(q_avg, 2))

    return {
        "labels": sorted_minutes,
        "p50": p50_list,
        "p95": p95_list,
        "p99": p99_list,
        "traffic": traffic_list,
        "error_rate": error_rate_list,
        "cost": cost_list,
        "tokens_in": tokens_in_list,
        "tokens_out": tokens_out_list,
        "quality": quality_list,
        "summary": {
            "total_records": len(records),
            "p95_overall": round(percentile(all_latencies, 95), 1),
            "total_received": total_received,
            "total_failed": total_failed,
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens_in + total_tokens_out,
            "quality_avg": round(sum(all_qualities) / len(all_qualities), 2) if all_qualities else 0.0
        }
    }

def generate_html(data):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Day 13 AI Observability Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid #334155;
        }}
        .header h1 {{ font-size: 24px; font-weight: 700; color: #38bdf8; }}
        .meta-badges {{ display: flex; gap: 12px; font-size: 13px; }}
        .badge {{ background: #1e293b; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }}
        @media (max-width: 1200px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        .card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 18px;
            position: relative;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .card-title {{ font-size: 15px; font-weight: 600; color: #e2e8f0; }}
        .threshold-label {{ font-size: 12px; color: #ef4444; font-weight: 600; background: rgba(239, 68, 68, 0.1); padding: 2px 8px; border-radius: 4px; }}
        .chart-container {{ position: relative; height: 220px; width: 100%; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Day 13 AI Observability Dashboard</h1>
            <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Data Source: <code>data/logs.jsonl</code> | Refresh: 30s | Time Range: 60m</p>
        </div>
        <div class="meta-badges">
            <div class="badge">Total Requests: <strong style="color:#38bdf8;">{data['summary']['total_received']}</strong></div>
            <div class="badge">P95 Latency: <strong style="color:#a855f7;">{data['summary']['p95_overall']}ms</strong></div>
            <div class="badge">Total Cost: <strong style="color:#22c55e;">${data['summary']['total_cost']}</strong></div>
            <div class="badge">Avg Quality: <strong style="color:#eab308;">{data['summary']['quality_avg']}</strong></div>
        </div>
    </div>

    <div class="grid">
        <!-- 1. Latency -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">1. Latency Percentiles (P50, P95, P99)</span>
                <span class="threshold-label">SLO: P95 ≤ 3000ms</span>
            </div>
            <div class="chart-container"><canvas id="chart-latency"></canvas></div>
        </div>

        <!-- 2. Traffic -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">2. Request Traffic (req/min)</span>
                <span class="threshold-label">Threshold: ≥ 1 rpm</span>
            </div>
            <div class="chart-container"><canvas id="chart-traffic"></canvas></div>
        </div>

        <!-- 3. Errors -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">3. Error Rate & Breakdown (%)</span>
                <span class="threshold-label">SLO: Error ≤ 2%</span>
            </div>
            <div class="chart-container"><canvas id="chart-errors"></canvas></div>
        </div>

        <!-- 4. Cost -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">4. Cost Over Time (USD)</span>
                <span class="threshold-label">Threshold: Total ≤ $2.50</span>
            </div>
            <div class="chart-container"><canvas id="chart-cost"></canvas></div>
        </div>

        <!-- 5. Tokens -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">5. Tokens (Input vs Output)</span>
                <span class="threshold-label">Threshold: Sum ≤ 50,000</span>
            </div>
            <div class="chart-container"><canvas id="chart-tokens"></canvas></div>
        </div>

        <!-- 6. Quality -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">6. Quality Proxy Score (0 - 1)</span>
                <span class="threshold-label">SLO: Mean ≥ 0.75</span>
            </div>
            <div class="chart-container"><canvas id="chart-quality"></canvas></div>
        </div>
    </div>

    <script>
        const labels = {json.dumps(data['labels'])};

        // Helper for threshold line plugin
        const createThresholdPlugin = (value, labelText, color = '#ef4444') => ({{
            id: 'thresholdLine_' + Math.random(),
            afterDraw(chart) {{
                const {{ ctx, chartArea: {{ left, right }}, scales: {{ y }} }} = chart;
                if (!y) return;
                const yPos = y.getPixelForValue(value);
                ctx.save();
                ctx.beginPath();
                ctx.setLineDash([6, 6]);
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.moveTo(left, yPos);
                ctx.lineTo(right, yPos);
                ctx.stroke();

                ctx.fillStyle = color;
                ctx.font = '11px sans-serif';
                ctx.fillText(labelText, right - 110, yPos - 6);
                ctx.restore();
            }}
        }});

        const chartOptions = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ labels: {{ color: '#94a3b8', boxWidth: 12 }} }} }},
            scales: {{
                x: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: '#1e293b' }} }},
                y: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: '#334155' }} }}
            }}
        }};

        // 1. Latency
        new Chart(document.getElementById('chart-latency'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'P50 (ms)', data: {json.dumps(data['p50'])}, borderColor: '#38bdf8', tension: 0.3 }},
                    {{ label: 'P95 (ms)', data: {json.dumps(data['p95'])}, borderColor: '#a855f7', tension: 0.3 }},
                    {{ label: 'P99 (ms)', data: {json.dumps(data['p99'])}, borderColor: '#f43f5e', tension: 0.3 }}
                ]
            }},
            options: chartOptions,
            plugins: [createThresholdPlugin(3000, 'SLO: 3000ms')]
        }});

        // 2. Traffic
        new Chart(document.getElementById('chart-traffic'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Requests/min', data: {json.dumps(data['traffic'])}, backgroundColor: '#38bdf8' }}]
            }},
            options: chartOptions,
            plugins: [createThresholdPlugin(1, 'Min: 1 rpm', '#22c55e')]
        }});

        // 3. Errors
        new Chart(document.getElementById('chart-errors'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Error Rate (%)', data: {json.dumps(data['error_rate'])}, borderColor: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', fill: true }}]
            }},
            options: chartOptions,
            plugins: [createThresholdPlugin(2.0, 'SLO: 2%')]
        }});

        // 4. Cost
        new Chart(document.getElementById('chart-cost'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Cost ($/min)', data: {json.dumps(data['cost'])}, backgroundColor: '#22c55e' }}]
            }},
            options: chartOptions,
            plugins: [createThresholdPlugin(2.5, 'Max: $2.50')]
        }});

        // 5. Tokens
        new Chart(document.getElementById('chart-tokens'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Tokens In', data: {json.dumps(data['tokens_in'])}, backgroundColor: '#6366f1' }},
                    {{ label: 'Tokens Out', data: {json.dumps(data['tokens_out'])}, backgroundColor: '#8b5cf6' }}
                ]
            }},
            options: {{ ...chartOptions, scales: {{ ...chartOptions.scales, x: {{ stacked: true }}, y: {{ stacked: true }} }} }},
            plugins: [createThresholdPlugin(50000, 'Limit: 50k')]
        }});

        // 6. Quality
        new Chart(document.getElementById('chart-quality'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Avg Quality Score', data: {json.dumps(data['quality'])}, borderColor: '#eab308', tension: 0.3 }}]
            }},
            options: chartOptions,
            plugins: [createThresholdPlugin(0.75, 'SLO: 0.75', '#eab308')]
        }});
    </script>
</body>
</html>
"""
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Dashboard generated successfully at: {OUTPUT_HTML}")
    webbrowser.open(OUTPUT_HTML.as_uri())

def main():
    data = parse_logs()
    generate_html(data)

if __name__ == "__main__":
    main()

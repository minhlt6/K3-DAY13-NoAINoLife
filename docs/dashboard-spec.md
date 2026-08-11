# Chi tiết đặc tả Dashboard (Dashboard Spec)

Contract kiểm tra tự động nằm tại [`config/dashboard.yaml`](../config/dashboard.yaml). Hướng dẫn dựng và kiểm tra runtime nằm tại [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md).

---

## 1. Danh sách 6 nhóm chỉ số bắt buộc

### 1. Latency (Độ trễ)
- **Tên panel**: Latency percentiles
- **Nguồn dữ liệu**: Endpoint `/metrics` (`latency_p50`, `latency_p95`, `latency_p99`) hoặc `data/logs.jsonl` (`latency_ms`)
- **Loại biểu đồ**: Line chart / Single value percentiles
- **Đơn vị**: `ms` (milliseconds)
- **Khoảng thời gian mặc định**: 60 phút (Refresh mỗi 30 giây)
- **Threshold / SLO line**: `P95 <= 3000 ms` (operator: `lte`, value: `3000`)

### 2. Traffic (Lưu lượng)
- **Tên panel**: Request traffic
- **Nguồn dữ liệu**: Endpoint `/metrics` (`traffic`) hoặc `data/logs.jsonl` (`request_received`)
- **Loại biểu đồ**: Counter / Rate per minute line chart
- **Đơn vị**: `requests_per_minute` (hoặc total requests)
- **Khoảng thời gian mặc định**: 60 phút (Refresh mỗi 30 giây)
- **Threshold / SLO line**: `Rate >= 1 req/min` (operator: `gte`, value: `1`)

### 3. Error (Tỷ lệ và phân loại lỗi)
- **Tên panel**: Error rate and breakdown
- **Nguồn dữ liệu**: Endpoint `/metrics` (`error_rate_pct`, `error_breakdown`) hoặc `data/logs.jsonl` (`request_failed`, `error_type`)
- **Loại biểu đồ**: Gauge (%) + Table breakdown theo `error_type`
- **Đơn vị**: `percent` (`%`)
- **Khoảng thời gian mặc định**: 60 phút (Refresh mỗi 30 giây)
- **Threshold / SLO line**: `Error Rate <= 2.0%` (operator: `lte`, value: `2`)

### 4. Cost (Chi phí)
- **Tên panel**: Cost over time
- **Nguồn dữ liệu**: Endpoint `/metrics` (`total_cost_usd`, `avg_cost_usd`) hoặc `data/logs.jsonl` (`cost_usd`)
- **Loại biểu đồ**: Bar / Area chart tích lũy chi phí
- **Đơn vị**: `usd` (`$`)
- **Khoảng thời gian mặc định**: 60 phút (Refresh mỗi 30 giây)
- **Threshold / SLO line**: `Total Cost <= $2.50` (operator: `lte`, value: `2.5`)

### 5. Tokens (Số lượng Token)
- **Tên panel**: Input and output tokens
- **Nguồn dữ liệu**: Endpoint `/metrics` (`tokens_in_total`, `tokens_out_total`) hoặc `data/logs.jsonl` (`tokens_in`, `tokens_out`)
- **Loại biểu đồ**: Bar chart song song Input vs Output tokens
- **Đơn vị**: `tokens`
- **Khoảng thời gian mặc định**: 60 phút (Refresh mỗi 30 giây)
- **Threshold / SLO line**: `Total Tokens <= 50,000` (operator: `lte`, value: `50000`)

### 6. Quality (Chất lượng phản hồi)
- **Tên panel**: Quality proxy
- **Nguồn dữ liệu**: Endpoint `/metrics` (`quality_avg`) hoặc `data/logs.jsonl` (`quality_score`)
- **Loại biểu đồ**: Gauge / Single Value average score
- **Đơn vị**: `score_0_to_1` (thang điểm từ 0.0 đến 1.0)
- **Khoảng thời gian mặc định**: 60 phút (Refresh mỗi 30 giây)
- **Threshold / SLO line**: `Quality Avg >= 0.75` (operator: `gte`, value: `0.75`)

---

## 2. Công cụ sử dụng & Cấu hình Runtime

- **Công cụ Dashboard**: Langfuse Observability / Custom Dashboard Contract spec (`config/dashboard.yaml`)
- **Endpoint kiểm tra dữ liệu**: `http://localhost:8000/metrics`
- **Mẫu dữ liệu thực tế thu được từ `/metrics`**:
  ```json
  {
    "traffic": 10,
    "latency_p50": 989.0,
    "latency_p95": 1072.0,
    "latency_p99": 1072.0,
    "avg_cost_usd": 0.002,
    "total_cost_usd": 0.0204,
    "tokens_in_total": 330,
    "tokens_out_total": 1291,
    "error_rate_pct": 0.0,
    "error_breakdown": {},
    "quality_avg": 0.88
  }
  ```

---

## 3. Lệnh kiểm tra Validator

Chạy lệnh kiểm tra contract dashboard trước khi nộp evidence:

```bash
python scripts/validate_dashboard.py
```

**Kết quả kiểm tra**:
`HỢP LỆ: 6/6 panel có trong dashboard contract.`

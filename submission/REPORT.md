# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (PASSED cả 4 tiêu chí)
- Tổng số traces: 25+ traces
- Số PII leak còn lại: 0 (Đã mã hóa Email, Phone VN, CCCD, Credit Card)
- Link/đường dẫn dashboard: `submission/evidence/dashboard.html`

## 3. Logging và tracing

- Evidence correlation ID: `req-bf91bef5`, `req-74e0b5b4`
- Evidence PII redaction: Các token `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]` xuất hiện trong `data/logs.jsonl`
- Evidence trace waterfall: Langfuse Trace Waterfall hiển thị các span `retrieve` (RAG) và `generate` (LLM)
- Giải thích một span đáng chú ý: Span `retrieve` xử lý thuật toán Vector Search lấy context domain. Trong kịch bản sự cố `rag_slow`, span này bị trễ ~2.5s dẫn tới kéo dài tổng latency của request.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: Version 1 (labels: `baseline`, `production`)
- Version/label candidate: Version 2 (labels: `candidate`)
- Trace ID của mỗi version: Baseline Trace ID (v1), Candidate Trace ID (v2) trên Langfuse UI
- Bằng chứng đổi label hoặc rollback: `submission/evidence/prompt_rollback.png`

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel`
- Evidence dashboard: `submission/evidence/dashboard.png`
- SLO đã chọn và lý do:
  - Latency P95 $\le$ 3000ms: Đảm bảo độ trễ phản hồi không làm gián đoạn trải nghiệm người dùng.
  - Error Rate $\le$ 2%: Đảm bảo độ tin cậy và khả năng sẵn sàng phục vụ của hệ thống API.
  - Daily Cost $\le$ $2.50: Kiểm soát ngân sách chi phí gọi API LLM Provider.
  - Quality Score $\ge$ 0.75: Đảm bảo chất lượng câu trả lời sinh ra.
- Alert rules và runbook: Đã cấu hình tại `config/alert_rules.yaml` và hướng dẫn xử lý tại `docs/alerts.md`

## 6. Điều tra challenge

- Challenge ID: day13-k3-observability-v1
- Triệu chứng từ metrics: Latency P95 tăng vọt vượt ngưỡng SLO 2000ms (đạt từ 2651ms đến 3399ms) trên Dashboard cho tính năng 'refund'.
- Trace ID liên quan: Langfuse Trace ID ứng với correlation_id `req-bf91bef5`
- Log line/correlation ID liên quan: `req-bf91bef5` (latency_ms: 3399), `req-74e0b5b4` (latency_ms: 2651)
- Root cause: Bước `retrieve()` trong RAG vector search bị delay nhân tạo 2.5s (do kịch bản incident `rag_slow` kích hoạt cho feature `refund`), làm tăng tổng độ trễ của API lên >2.6s.
- Fix action: Tắt incident qua API (`python scripts/inject_incident.py --disable`), thêm timeout 1000ms cho `retrieve()` và trả dữ liệu cached fallback khi quá hạn.
- Preventive measure: Thiết lập Alert Rule `high_latency_p95` (cảnh báo khi P95 > 3000ms), áp dụng Circuit Breaker & Timeout cho RAG Service và bật Caching cho các truy vấn phổ biến.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |

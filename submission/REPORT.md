# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: NoAINoLife
- Repository URL: https://github.com/minhlt6/K3-DAY13-NoAINoLife
- Commit SHA cuối: 2fb219c6d7c0bca2b65cd954c7020677d6f471d5
- Thành viên và vai trò:
  1. Hoàng Duy Linh - 2A202601159 (Nhóm trưởng - QA & Incident Analyst)
  2. Lê Tiến Minh - 2A202601193 (Logging & Middleware Specialist)
  3. Nguyễn Tuấn Anh - 2A202601395 (Security & Compliance Specialist)
  4. Nguyễn Phúc Huy Hoàng - 2A202601951 (Metrics & Alerting Specialist)

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (Bằng chứng: [`submission/evidence/validate_logs_score.png`](evidence/validate_logs_score.png))
- Tổng số traces: 10
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: [`submission/evidence/dashboard_config.png`](evidence/dashboard_config.png)

## 3. Logging và tracing

- Evidence correlation ID: [`submission/evidence/logs_pii_redacted.png`](evidence/logs_pii_redacted.png) (log line chứa `"correlation_id": "req-58fda279"`)
- Evidence PII redaction: [`submission/evidence/logs_pii_redacted.png`](evidence/logs_pii_redacted.png) (log line chứa `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`)
- Evidence trace waterfall: [`submission/evidence/trace_waterfall.png`](evidence/trace_waterfall.png) (Danh sách traces: [`submission/evidence/traces_list.png`](evidence/traces_list.png), Metadata: [`submission/evidence/trace_generation_metadata.png`](evidence/trace_generation_metadata.png))
- Giải thích một span đáng chú ý: Span `run` (Generation) đo tổng thời gian xử lý LLM request bao gồm retrieve context, fetch prompt version, và gọi LLM generate answer.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: `production` (`v1` / `local-v1`)
- Version/label candidate: `staging` (`v2`)
- Trace ID của mỗi version: Các trace được tự động gắn metadata `prompt_name=day13-chat`, `prompt_label=production`, `prompt_version=local-v1`
- Bằng chứng đổi label hoặc rollback: Tích hợp hàm `resolve_prompt()` trong `app/prompt_management.py` và bộ kiểm thử tự động `tests/test_prompt_management.py` (đạt 100% test coverage).

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ: 6/6 panel có trong dashboard contract.
- Evidence dashboard: [`submission/evidence/dashboard_config.png`](evidence/dashboard_config.png) (Cấu hình tại [`config/dashboard.yaml`](../config/dashboard.yaml) & [`docs/dashboard-spec.md`](../docs/dashboard-spec.md)).
- SLO đã chọn và lý do:
  - Latency P95 <= 3000ms: Đảm bảo phản hồi nhanh cho người dùng ứng dụng AI Chatbot.
  - Error Rate <= 2.0%: Đảm bảo tính sẵn sàng và ổn định của dịch vụ RAG LLM.
  - Daily Cost <= $2.50: Đảm bảo kiểm soát chi phí API LLM không vượt ngân sách.
  - Quality Score Avg >= 0.75: Đảm bảo chất lượng câu trả lời từ RAG context.
- Alert rules và runbook: Quy định tại [`config/alert_rules.yaml`](../config/alert_rules.yaml) và [`docs/alerts.md`](../docs/alerts.md).

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`
- Triệu chứng từ metrics: Latency P95/P99 của feature `refund` khi chạy tải đồng thời (`--concurrency 5`) tăng đột biến từ ~1000ms lên **10,920ms – 18,041ms** (vượt quá nhiều so với ngưỡng quy định 2000ms, xem Bằng chứng Terminal: [`submission/evidence/challenge_terminal_result.png`](evidence/challenge_terminal_result.png)).
- Trace ID liên quan: Xem các trace ứng với feature `refund` trên Langfuse Dashboard (Bằng chứng Metadata: [`submission/evidence/trace_generation_metadata.png`](evidence/trace_generation_metadata.png)).
- Log line/correlation ID liên quan: `req-1dcf1a71`, `req-e3b55665`, `req-229179d0`, `req-a12eb1f6`, `req-6e120a82` (ghi nhận trong [`data/logs.jsonl`](../data/logs.jsonl)).
- Root cause: Incident `rag_slow` ảnh hưởng tới feature `refund`, khi bị tải đồng thời khâu RAG retrieval/context synthesis gây ra tắc nghẽn nghiêm trọng.
- Fix action: Tắt incident sự cố bằng lệnh `python scripts/inject_incident.py --disable`.
- Preventive measure: Đặt timeout cho khâu RAG retrieval, bổ sung bộ nhớ đệm (cache) cho tài liệu truy vấn thường gặp và thiết lập cảnh báo `high_latency_p95`.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Hoàng Duy Linh - 2A202601159 (Nhóm trưởng) | **QA & Incident Analyst**: Chạy load test sinh dữ liệu, thiết kế Dashboard Spec (`docs/dashboard-spec.md`), chủ trì điều tra Challenge (CP3) và hoàn thiện báo cáo `REPORT.md`. | Commit [`403d109`](https://github.com/minhlt6/K3-DAY13-NoAINoLife/commit/403d109f829ec9758a742db94ce1f0af57557622) | Nắm vững quy trình điều tra sự cố 3 lớp (Metrics → Traces → Logs), kỹ năng phân tích và tổng hợp báo cáo. |
| Lê Tiến Minh - 2A202601193 | **Logging & Middleware**: Phụ trách CP1 — Xây dựng `CorrelationIdMiddleware`, xử lý đính kèm header `x-request-id` và gán log metadata với `bind_contextvars`. | Commit [`2fb219c`](https://github.com/minhlt6/K3-DAY13-NoAINoLife/commit/2fb219c6d7c0bca2b65cd954c7020677d6f471d5) | Hiểu sâu kiến trúc FastAPI Middleware, quản lý contextvars và luồng dữ liệu log hệ thống. |
| Nguyễn Tuấn Anh - 2A202601395 | **Security & Compliance**: Phụ trách CP1 — Uncomment `scrub_event` processor, cấu hình regex patterns che PII (`email`, `phone`, `cccd`, `credit_card`, `passport`, `address_vn`) và nâng cấp che PII toàn cục. | Commit [`8be56c7`](https://github.com/minhlt6/K3-DAY13-NoAINoLife/commit/8be56c704db784522ab675108d780342fc276961) | Nắm vững kỹ thuật PII scrubbing, bảo mật thông tin người dùng trong JSON logging theo tiêu chuẩn compliance. |
| Nguyễn Phúc Huy Hoàng - 2A202601951 | **Metrics & Alerting**: Phụ trách CP2 — Tích hợp Langfuse SDK Tracing, đo đếm chỉ số `error_rate_pct`, viết SLO (`config/slo.yaml`), Alert rules (`config/alert_rules.yaml`) và Runbook (`docs/alerts.md`). | Commit [`5cbb458`](https://github.com/minhlt6/K3-DAY13-NoAINoLife/commit/5cbb458cac2fbd4c7070b0ef4fb4956822f01d3d) | Thành thạo tích hợp APM/Langfuse SDK, xây dựng SLO/SLI và thiết kế hệ thống cảnh báo symptom-based. |

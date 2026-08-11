# Alert và runbook

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO. Điều tra theo luồng
Metrics → Traces → Logs và dùng correlation ID để nối bằng chứng.

## Alert 1: High latency

- Tên: `high_latency_p95`
- Severity: warning
- SLI/SLO liên quan: P95 latency ≤ 3000 ms.
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời chậm, tăng tỷ lệ bỏ phiên.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận P50/P95/P99 và thời điểm bắt đầu tăng trên dashboard.
  2. Mở trace chậm trong cùng khoảng thời gian, so sánh `rag.retrieve` và `llm.generate`.
  3. Tìm log bằng correlation ID của trace và kiểm tra incident/trạng thái dependency.
- Mitigation tạm thời: tắt incident `rag_slow`, giảm concurrency hoặc dùng local prompt fallback nếu Langfuse fetch chậm.
- Owner: `platform-observability`.

## Alert 2: High error rate

- Tên: `high_error_rate`
- Severity: critical
- SLI/SLO liên quan: error rate ≤ 2%.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục 5 phút.
- Ảnh hưởng tới người dùng: request `/chat` trả HTTP 5xx hoặc không có câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Xem breakdown theo `error_type` để xác định lỗi chiếm ưu thế.
  2. Mở một trace lỗi và xác định span thất bại đầu tiên.
  3. Tra log `request_failed` cùng correlation ID và kiểm tra payload đã được redact.
- Mitigation tạm thời: tắt incident `tool_fail`, cô lập dependency lỗi và giữ local fallback hoạt động.
- Owner: `platform-observability`.

## Alert 3: Low quality score

- Tên: `low_quality_score`
- Severity: warning
- SLI/SLO liên quan: quality proxy trung bình ≥ 0.75.
- Điều kiện và thời gian duy trì: `quality_score_avg < 0.75` liên tục 10 phút.
- Ảnh hưởng tới người dùng: câu trả lời ít liên quan, thiếu context hoặc không đủ chi tiết.
- Ba bước kiểm tra đầu tiên:
  1. Khoanh vùng feature/session có quality thấp trên dashboard và logs.
  2. Kiểm tra trace metadata `prompt_name`, `prompt_label`, `prompt_version` và số document retrieve.
  3. So sánh prompt version hiện tại với baseline; kiểm tra có vừa đổi label hay không.
- Mitigation tạm thời: rollback label `production` về prompt baseline v1 và xác nhận bằng trace mới.
- Owner: `ai-application`.

## Sau khi xử lý

Ghi lại thời điểm, SLI trước/sau, trace ID, correlation ID, root cause, mitigation và
preventive action trong `submission/REPORT.md` hoặc báo cáo incident tương ứng.

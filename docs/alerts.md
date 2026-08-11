# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

<a id="alert-1"></a>
## Alert 1: high_latency_p95

- **Tên**: high_latency_p95
- **Severity**: warning
- **SLI/SLO liên quan**: `latency_p95_ms` (SLO: P95 <= 3000ms cho 99.5% requests)
- **Điều kiện và thời gian duy trì**: `latency_p95 > 3000ms for 5 minutes`
- **Ảnh hưởng tới người dùng**: Phản hồi từ ứng dụng Chatbot bị chậm trễ kéo dài, gây trễ hiển thị câu trả lời cho người dùng.
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra Dashboard panel **Latency percentiles** để xác định thời điểm tăng đột biến P95/P99.
  2. Truy cập Langfuse Dashboard lọc các Traces chậm nhất để phân tích span timeline (xem trễ ở RAG retrieval hay LLM generation).
  3. Kiểm tra log `data/logs.jsonl` theo `correlation_id` của trace chậm để phát hiện lỗi timeout hoặc nghẽn tài nguyên.
- **Mitigation tạm thời**: Chuyển sang prompt ngắn gọn hơn hoặc giảm số lượng tài liệu retrieved context trong RAG để hạ độ trễ.
- **Owner**: on-call-engineer

<a id="alert-2"></a>
## Alert 2: elevated_error_rate

- **Tên**: elevated_error_rate
- **Severity**: critical
- **SLI/SLO liên quan**: `error_rate_pct` (SLO: Error rate <= 2.0% cho 99.0% requests)
- **Điều kiện và thời gian duy trì**: `error_rate_pct > 5 for 3 minutes`
- **Ảnh hưởng tới người dùng**: Người dùng gặp lỗi HTTP 500 liên tục khi gửi câu hỏi, dịch vụ chatbot không phản hồi.
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra panel **Error rate and breakdown** trên Dashboard để xác định loại lỗi chính (`error_type`).
  2. Tra cứu log sự kiện `request_failed` trong `data/logs.jsonl` để lấy `payload.detail` và `correlation_id` của lỗi.
  3. Kiểm tra trạng thái mạng, các API key và trạng thái server phụ thuộc (ví dụ LLM Provider API status).
- **Mitigation tạm thời**: Khởi động lại dịch vụ API hoặc bật chế độ fallback response cho tính năng gặp sự cố để đảm bảo khả năng phục vụ.
- **Owner**: on-call-engineer

<a id="alert-3"></a>
## Alert 3: cost_budget_exceeded

- **Tên**: cost_budget_exceeded
- **Severity**: warning
- **SLI/SLO liên quan**: `daily_cost_usd` (SLO: Chi phí <= $2.5/ngày cho 100.0% ngân sách)
- **Điều kiện và thời gian duy trì**: `daily_cost_usd > 2.5`
- **Ảnh hưởng tới người dùng**: Không ảnh hưởng trực tiếp tới trải nghiệm người dùng nhưng gây rủi ro vượt ngân sách dự án.
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra panel **Cost over time** trên Dashboard để xem tốc độ tiêu tốn chi phí theo thời gian.
  2. Lọc các trace có `cost_usd` cao nhất trên Langfuse để kiểm tra `tokens_in` / `tokens_out` bất thường.
  3. Kiểm tra traffic bất thường (tấn công bot hoặc luồng request lặp vô hạn) gây tăng tiêu thụ token.
- **Mitigation tạm thời**: Áp dụng Rate Limiting chặt hơn hoặc tạm thời hạ model về phiên bản tiết kiệm chi phí hơn.
- **Owner**: team-lead

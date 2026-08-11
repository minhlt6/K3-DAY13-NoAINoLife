# Runbook Chi Tiết Cho Các Alert System

Tài liệu hướng dẫn xử lý sự cố (Runbook) cho các cảnh báo tự động trong hệ thống Observability Day 13.

---

## Alert 1: high_latency_p95

- **Tên:** `high_latency_p95`
- **Severity:** `warning`
- **SLI/SLO liên quan:** `latency_p95_ms` (SLO: Latency P95 ≤ 3000ms, Target: 99.5% requests)
- **Điều kiện và thời gian duy trì:** `latency_p95 > 3000ms for 5 minutes`
- **Ảnh hưởng tới người dùng:** Người dùng bị phản hồi chậm khi gửi câu hỏi tới AI Chat, giao diện quay vòng lâu, nguy cơ gây ra timeout trên ứng dụng client.
- **Ba bước kiểm tra đầu tiên:**
  1. **Kiểm tra Dashboard:** Mở panel *Latency percentiles* trên Dashboard để xác định xem độ trễ tăng đột biến trên tất cả tính năng hay chỉ xuất hiện ở một `feature` cụ thể (`qa` hoặc `summary`).
  2. **Kiểm tra Langfuse Traces:** Truy cập Langfuse, lọc các trace có `latency > 3000ms`, soi chi tiết từng span (`retrieve` từ RAG vs gọi LLM API) để khoanh vùng chính xác bước gây nghẽn.
  3. **Kiểm tra Logs:** Lọc `data/logs.jsonl` theo `correlation_id` của các trace chậm để phân tích log nội bộ (`doc_count` quá lớn, độ trễ vector search, hoặc timeout mạng).
- **Mitigation tạm thời:**
  - Giảm bớt số lượng tài liệu truy vấn `doc_count` trong bước RAG.
  - Chuyển tạm thời sang phiên bản prompt ngắn hơn (`baseline`).
  - Áp dụng Caching cho các câu hỏi phổ biến và bật Rate Limiting đối với nguồn traffic quá tải.
- **Owner:** `on-call-engineer`

---

## Alert 2: elevated_error_rate

- **Tên:** `elevated_error_rate`
- **Severity:** `critical`
- **SLI/SLO liên quan:** `error_rate_pct` (SLO: Error Rate ≤ 2%, Target: 99.0% availability)
- **Điều kiện và thời gian duy trì:** `error_rate_pct > 5 for 3 minutes`
- **Ảnh hưởng tới người dùng:** Người dùng liên tục nhận lỗi (500 Internal Server Error / Request Failed), câu trả lời không được tạo ra, dịch vụ AI bị gián đoạn.
- **Ba bước kiểm tra đầu tiên:**
  1. **Kiểm tra Dashboard:** Mở panel *Error rate and breakdown* trên Dashboard để theo dõi tỷ lệ lỗi và xem phân rã các loại lỗi phổ biến (`error_type`).
  2. **Kiểm tra Logs:** Lọc trong `data/logs.jsonl` các dòng log có `event == "request_failed"` để xem chính xác `error_type`, thông điệp lỗi chi tiết và `correlation_id`.
  3. **Kiểm tra Traces & External Services:** Mở Trace tương ứng trên Langfuse để kiểm tra trạng thái kết nối tới nhà cung cấp LLM (hết quota, sai API key, rate limit) hoặc lỗi kết nối tới cơ sở dữ liệu RAG.
- **Mitigation tạm thời:**
  - Chuyển hướng lưu lượng (failover) sang LLM model/provider dự phòng hoặc tự động kích hoạt `local-fallback` prompt.
  - Khởi động lại service API hoặc bật Circuit Breaker tạm thời ngắt dịch vụ phụ trợ đang gặp lỗi.
- **Owner:** `on-call-engineer`

---

## Alert 3: cost_budget_exceeded

- **Tên:** `cost_budget_exceeded`
- **Severity:** `warning`
- **SLI/SLO liên quan:** `daily_cost_usd` (SLO: Daily Cost ≤ $2.50, Target: 100.0%)
- **Điều kiện và thời gian duy trì:** `daily_cost_usd > 2.5`
- **Ảnh hưởng tới người dùng:** Không ảnh hưởng trực tiếp tới trải nghiệm người dùng tức thì, nhưng nguy cơ vượt ngân sách vận hành, có thể dẫn đến việc tài khoản LLM API bị ngắt đột ngột do hết hạn mức.
- **Ba bước kiểm tra đầu tiên:**
  1. **Kiểm tra Dashboard:** Mở panel *Cost over time* và *Tokens* trên Dashboard để xem tổng chi phí trong ngày và tốc độ gia tăng chi phí theo từng phút.
  2. **Kiểm tra Langfuse Traces:** Lọc các trace có `cost_usd` hoặc `completion_tokens` cao bất thường để tìm ra model hoặc user/session nào đang sử dụng quá nhiều token.
  3. **Kiểm tra Logs:** Tìm các dòng log `event == "response_sent"` sắp xếp theo `cost_usd` hoặc `tokens_out` giảm dần để phát hiện các request bất thường (ví dụ: prompt injection khiến AI trả lời vô tận, lặp lại).
- **Mitigation tạm thời:**
  - Giới hạn `max_tokens` của câu trả lời LLM.
  - Chuyển tạm thời sang model nhỏ hơn có chi phí rẻ hơn.
  - Áp dụng Rate Limit khắt khe đối với các `user_id_hash` / `session_id` đang gửi request liên tục với lượng token lớn.
- **Owner:** `team-lead`

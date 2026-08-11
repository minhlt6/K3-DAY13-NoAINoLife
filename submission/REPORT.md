# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (`submission/evidence/01-validate-logs.png.jpg`)
- Tổng số traces: 69 (xác nhận qua Langfuse API ngày 2026-08-11)
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: `http://localhost:8501` (`streamlit run streamlit_app.py`)

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/02-correlation-pii-redaction.png.jpg`
- Evidence PII redaction: `submission/evidence/02-correlation-pii-redaction.png.jpg`
- Evidence trace waterfall: `submission/evidence/trace_waterfall.jpg`; trace mới: `7913bba4e140df54704599220eaff912`
- Giải thích một span đáng chú ý: `agent.run` là generation gốc; `rag.retrieve` và `llm.generate` là hai span con. Khi bật `rag_slow`, thời gian `rag.retrieve` tăng và dashboard P95 vượt 3000 ms; dùng correlation ID trong trace metadata để tìm log cùng request.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: version 1, labels `baseline` và `production` sau rollback
- Version/label candidate: version 2, label `candidate`
- Trace ID của mỗi version: baseline/v1 `7913bba4e140df54704599220eaff912`; candidate/v2 `0b7c47a8c59df2736d75ce36fce62687`
- Bằng chứng đổi label hoặc rollback: `submission/evidence/06-prompt-versions-api.png`, `submission/evidence/07-prompt-rollback-api.png` và audit đầy đủ `submission/evidence/prompt-versioning.json`. Production/v2 trace `dd526c4ae338da3a634a8c0a4051b360`; production/v1 sau rollback `74dca0a6055732e3954c9bb9d8910b64`.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.` (`submission/evidence/03-dashboard-validator.png`)
- Evidence dashboard: baseline `submission/evidence/04-dashboard-runtime.png`; incident `rag_slow` `submission/evidence/05-dashboard-rag-slow.png`
- SLO đã chọn và lý do: P95 ≤ 3000 ms để giữ trải nghiệm tương tác; error rate ≤ 2%; daily cost ≤ 2.5 USD; quality trung bình ≥ 0.75. Chi tiết tại `config/slo.yaml`.
- Alert rules và runbook: ba alert symptom-based cho latency, error rate và quality tại `config/alert_rules.yaml`; hướng dẫn Metrics → Traces → Logs tại `docs/alerts.md`.

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |

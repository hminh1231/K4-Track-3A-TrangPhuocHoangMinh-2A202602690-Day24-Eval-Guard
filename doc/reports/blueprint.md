# Blueprint CI/CD cho RAG và guardrails

Nhóm: TrangPhuocHoangMinh (làm cá nhân)

Người phụ trách: Trang Phước Hoàng Minh — 2A202602690

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: guard 2026-10-12T15:41:50Z (Phase A 15:39:22Z, Phase B 15:39:56Z); guard models: `gpt-4o-mini`.
Models generation/evaluator/judge từ A/B: generation `gpt-4o-mini-2024-07-18` (answers_50q.json);
evaluator `gpt-4o-mini` + `text-embedding-3-small` (ragas_50q.json, do m4 khai báo); judge
`gpt-4o-mini` (judge_results.json).

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

| Tầng | Kiểm tra | Khi phát hiện | Bằng chứng trong lab |
|---|---|---|---|
| Presidio (local, regex + spaCy) | VN_CCCD (12/9 số), VN_PHONE, EMAIL, PHONE_NUMBER, thẻ/IBAN | Chặn request, trả câu từ chối, log chỉ bản đã redact (`<VN_CCCD>`) | Chặn 4/4 câu pii_injection có định danh (id 1–4) |
| NeMo input rail (self check input) | Off-topic, jailbreak, role/authority impersonation, prompt injection, xin dữ liệu người khác | Chặn, trả `bot refuse to respond`, log tên rail | Chặn 16/16 attack còn lại (id 5–20), 0/8 câu sạch bị chặn |
| RAG (m1–m5) | Hybrid search + rerank, generation gpt-4o-mini | Lỗi API → `extractive_fallback`, ghi `generation_mode` | 50/50 câu ở mode llm |
| NeMo output rail (self check output) | CCCD/SĐT/email riêng, lương cá nhân, credential, hồ sơ mật | Thay answer bằng câu từ chối, giữ nguyên answer sạch | 4/4 output case đúng (201, 202 giữ nguyên; 203, 204 bị thay) |

Data flow và vận hành:

- Presidio chạy trước để PII không bao giờ đi tới LLM bên ngoài; chỉ chuỗi đã anonymize được ghi log.
- Presidio chỉ chặn các entity dạng định danh. spaCy `en_core_web_lg` gắn nhầm PERSON/DATE_TIME/NRP
  cho văn bản tiếng Việt, nên các entity đó bị loại khỏi quyết định chặn để tránh false positive.
- Secrets (`OPENAI_API_KEY`) chỉ nằm trong `.env`/secret store của CI, không vào log hay artifacts.
- Fail-closed cho guard: nếu NeMo input/output lỗi hoặc timeout, trả câu từ chối thay vì cho qua;
  fail-open có kiểm soát cho RAG: lỗi generation chuyển sang `extractive_fallback` và gắn cờ.
- Prompt self-check input đã được làm rõ phạm vi (danh sách chủ đề HR/IT được phép, mọi thứ ngoài
  phạm vi là chặn, câu trộn câu hỏi hợp lệ với injection vẫn chặn, quy tắc tài khoản như khóa sau N
  ngày là câu hỏi chính sách). Prompt gốc cho qua câu off-topic (bài thơ) và bản sửa đầu chặn nhầm
  câu sạch 106 (khóa tài khoản VPN); bản cuối đạt 28/28 ở hai lượt thử trước khi chạy runner.
  Lưu ý: prompt được chỉnh dựa trên chính bộ 28 câu này, nên kết quả 20/20 và 8/8 có rủi ro overfit
  — cần bộ held-out mới để xác nhận.

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 13.23 | 16.97 | 18.18 | Đo thật Task 12, nhanh và ổn định (11.6–18.5 ms) |
| NeMo input | 673.30 | 824.27 | 2260.75 | Đo thật Task 12, chiếm khoảng 98% thời gian (593.4–2619.9 ms) |
| Input guard sequential | 686.00 | 841.05 | 2275.88 | Đo thật Task 12, vượt target 500 ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế/budget_ok: P95 841.05 ms, `latency_budget_ok = false`.

Bottleneck là NeMo input rail: mỗi request là một lượt gọi API gpt-4o-mini qua mạng (self check
input), nên latency do round-trip và hàng đợi của provider quyết định, không phải CPU local. Presidio
chỉ khoảng 13 ms. P99 2275.88 ms do một mẫu NeMo 2619.9 ms — đuôi latency của API bên ngoài,
đúng loại rủi ro cần timeout + fail-closed. Hướng giảm: (1) chạy Presidio và NeMo song song rồi kết hợp quyết định (latency ≈
max thay vì tổng); (2) giới hạn `max_tokens` của self-check về 1–3 token; (3) cache quyết định cho
câu hỏi lặp lại; (4) thay self-check LLM bằng classifier local (ví dụ embedding + logistic) cho
off-topic, chỉ gọi LLM với ca nghi ngờ; (5) đặt server gần region của provider. Mỗi thay đổi cần đo
lại cùng phương pháp (2 warm-up, ≥20 mẫu, nội suy tuyến tính).

Kế hoạch đo phần "chưa đo": ghi `perf_counter` tại 5 mốc (nhận request, sau input guard, sau
retrieval+rerank, sau generation, sau output rail) cho ≥50 request sạch và ≥20 request bị chặn, sau
2 warm-up; báo cáo riêng RAG, output rail và end-to-end có short-circuit. Không dùng
input_guard_ms để kết luận full guard đạt hay không đạt 500 ms.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.

Đối chiếu với kết quả hiện tại: faithfulness tổng = (0.923×20 + 0.465×20 + 0.700×10)/50 = 0.695
→ **không đạt** gate 0.75; avg_score tổng = 0.724 → đạt; attacks 20/20, clean 8/8, output 4/4 → đạt;
input guard P95 841.05 ms → chỉ ghi nhận, chưa thành gate vì chưa đo full guard.

Pipeline đề xuất (chưa triển khai, chưa có file workflow trong repo):

1. Job `unit` (mọi PR): `python -m pytest tests/ -q` — không gọi API, fail nếu có test fail.
2. Job `eval-live` (nightly hoặc PR đổi prompt/model/corpus, dùng secret store):
   `python scripts/setup_answers.py --live`, rồi lần lượt
   `python scripts/run_experiments.py --phase a --live`, `--phase b --live`,
   `--phase c --live --latency-samples 20`.
3. Job `gate`: `python scripts/check_lab.py` (hiện đã trả nonzero khi schema/số đếm sai, attacks
   <15/20 hoặc có false positive), cộng một script gate mới đọc ngưỡng từ biến `MIN_FAITHFULNESS`,
   `MIN_AVG_SCORE`, `MIN_ATTACKS_PASSED`, `MAX_FALSE_POSITIVE` và `sys.exit(1)` khi không đạt. Các
   biến MIN_* chỉ có tác dụng khi script này được viết; runner hiện tại chưa kiểm tra các ngưỡng đó.
4. Lưu 4 file JSON làm artifact của job để so sánh giữa các lần chạy (diff mean theo distribution).

## Monitoring và cải tiến

| Metric | Cách lấy mẫu | Ngưỡng cảnh báo | Hành động |
|---|---|---|---|
| Tỉ lệ request bị chặn theo tầng | Đếm log blocked_by mỗi giờ | Tăng/giảm >2 lần so với trung bình 7 ngày | Đọc mẫu: tấn công mới hay false positive |
| False positive | Người dùng báo "bị chặn nhầm" + review 20 mẫu bị chặn/tuần | >1/20 mẫu review là câu sạch | Thêm câu vào clean set, sửa prompt, chạy lại 28 + held-out |
| Tỉ lệ answer "Không tìm thấy" | Đếm theo ngày | >10% câu hỏi in-scope (mốc lab 7/50 = 14%) | Kiểm tra retrieval/prompt (lỗi over-refusal Phase A) |
| Faithfulness online | RAGAS trên 2% traffic đã redact PII | <0.7 trung bình tuần | Mở incident chất lượng, chạy lại eval 50 câu |
| Input guard P95 | perf_counter mỗi request | >1000 ms trong 15 phút | Kiểm tra provider/region, bật cache |
| Judge drift | 10 nhãn người/tháng, tính κ | κ <0.6 | Ngừng dùng judge làm gate, sửa prompt judge |
| Corpus/version drift | Hash tài liệu trong `data/` | Có file mới/đổi phiên bản | Chạy lại toàn bộ eval-live, bổ sung câu adversarial phiên bản |

Privacy: log chỉ lưu văn bản đã qua Presidio anonymize, không lưu CCCD/SĐT/email gốc; mẫu dùng để
review được giữ có thời hạn. Người xử lý: owner pipeline (hiện là cá nhân thực hiện lab) nhận cảnh báo.

Giới hạn bộ đo: 50 câu RAG, 20 attack, 8 câu sạch và 4 output là bộ nhỏ; 8 câu sạch không đại diện
đủ traffic thật (ví dụ câu hỏi lương có nhắc tên người, câu hỏi tiếng Anh). Bộ 28 input đã được dùng
để chỉnh prompt nên cần held-out set.

RAGAS mean/worst distribution: factual 0.828, multi_hop 0.644 (yếu nhất), adversarial 0.673.
Cohen’s κ: 1.0 (10/10 nhãn khớp human).
Attacks passed: 20/20; clean false_positive_rate: 0.0.

Cải tiến có thể kiểm tra:

1. Đưa parent chunk (2048 ký tự) vào prompt thay cho 3 child chunk → đo lại context_recall và
   avg_score multi_hop (mốc 0.796 và 0.644).
2. Sửa prompt generation để trả lời phần có bằng chứng và ưu tiên phiên bản hiện hành → đếm lại số
   answer "Không tìm thấy" (mốc 7/50) và mean adversarial (mốc 0.673).
3. Chạy song song Presidio và NeMo input, giới hạn token self-check → đo lại input guard P95 (mốc
   841.05 ms) với cùng 2 warm-up + 20 mẫu.
4. Viết held-out set 20 attack + 20 câu sạch mới, không dùng để chỉnh prompt → báo cáo pass rate và
   false positive riêng để kiểm tra overfit của prompt self-check.
5. Thêm script gate đọc MIN_* và cho trả nonzero → xác nhận job fail khi faithfulness 0.695 < 0.75.

# Nhóm thực hiện K4 Track 3A

Tên nhóm: TrangPhuocHoangMinh (làm cá nhân, không theo nhóm)

Repo chung: https://github.com/hminh1231/K4-Track-3A-TrangPhuocHoangMinh-2A202602690-Day24-Eval-Guard

Trưởng nhóm/người nộp: Trang Phước Hoàng Minh — 2A202602690

Ngày lab/deadline áp dụng: 2026-10-12, 23:59 theo thông báo lớp — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: commit mới nhất trên nhánh `main` tại thời điểm nộp link (SHA ghi kèm khi gửi bài qua vlearn).

Bài làm cá nhân: một thành viên thực hiện toàn bộ chuẩn bị, ba phase, báo cáo và nộp bài.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Trang Phước Hoàng Minh | 2A202602690 | Toàn bộ: tích hợp m1–m5 (Day 18), Phase A Tasks 1–4, Phase B Tasks 5–8, Phase C Tasks 9a–12, prompt guardrails, ba báo cáo và Task 13 | Commit trên `main`; `src/phase_*.py`, `src/m1–m5`; `artifacts/*.json`; `doc/reports/*.md` |

Người tích hợp/chạy batch/nộp link: Trang Phước Hoàng Minh — chạy `setup_answers.py --live`, ba runner `--live`, `check_lab.py` và nộp link.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows 11 Home 10.0.26200; Python 3.12.10 (máy không có 3.11 như khuyến nghị); Microsoft C++ Build Tools 2022 (MSVC 14.44) cài qua winget để build `annoy==1.17.3`.
Virtualenv/dependencies/imports: `.venv` + `pip install -r requirements/requirements.txt -c requirements/constraints-core.txt`; phải hạ `pyarrow` xuống 17.0.0 và `pandas` xuống 2.2.3 vì bản mới yêu cầu NumPy 2 xung đột với pin `numpy==1.26.4`; `pip check` sạch; import ragas 0.1.22, nemoguardrails 0.10.0, presidio, spacy, annoy thành công. Trên Windows cần nạp torch trước pyarrow, nếu không torch báo lỗi DLL (WinError 1114).
Models/Qdrant/50 answers đã chuẩn bị: Qdrant `qdrant/qdrant:v1.9.7` qua Docker; BGE-M3 và bge-reranker-v2-m3 từ cache HuggingFace; spaCy `en_core_web_lg` 3.8.0; `artifacts/answers_50q.json` có 50 câu 20/20/10, cả 50 ở `generation_mode = llm` (`gpt-4o-mini-2024-07-18`), không có fallback. Hai PDF scan (`BCTC.pdf`, `Nghi_dinh_so_13-2023...pdf`) không có text layer nên m1 bỏ qua. NeMo 0.10.0 chạy thật trên Python 3.12 trong Phase C (input/output rail, 28 input + 4 output + latency).

## INDIVIDUAL

### TrangPhuocHoangMinh-2A202602690

- Phần được giao và phần thực tế đã làm: toàn bộ bài. Chép m1–m5 từ repo Day 18 và sửa adapter: m4 khai báo `metadata.evaluator_models`, truyền rõ evaluator LLM/embedding, chấm lại các dòng NaN thay vì điền số giả; m5 enrichment song song giữ thứ tự; m2 dùng `search()` cho qdrant-client 1.9. Phase A: group/run_ragas/bottom_10/cluster_analysis, thêm phân loại over-refusal cho câu trả "Không tìm thấy". Phase B: pairwise judge JSON có reference, swap-and-average quy đổi winner/scores, Cohen κ, bias report. Phase C: pii_scan lọc entity định danh, input/output rail đọc quyết định từ `activated_rails`, adversarial suite, đo latency hai tầng. Chỉnh prompt self check input trong `guardrails/config.yml`.
- Bằng chứng: commit trên `main`; `artifacts/answers_50q.json`, `ragas_50q.json`, `judge_results.json`, `guard_results.json`; `doc/reports/failure_clusters.md`, `bias_report.md`, `blueprint.md`.
- Cách kiểm tra: `python -m pytest tests/ -q` → 86 passed (mock, không gọi API); ba runner `--live` lưu JSON thật; `python scripts/check_lab.py` đối chiếu schema, nguồn, phép tính. Kết quả chính: multi_hop yếu nhất (0.644), κ = 1.0, attacks 20/20, clean 8/8, output 4/4, input guard P95 841.05 ms (vượt 500 ms).
- Điều đã học: RAGAS cho faithfulness 0 cả với câu từ chối nên phải đọc answer/contexts trước khi gán "hallucination"; winner A/B và nhãn tốt/xấu 0/1 là hai câu hỏi khác nhau; swap thứ tự để phát hiện position bias và chỉ số verbosity cần đọc nội dung mới kết luận; clean controls cần thiết vì guard luôn-chặn cũng đạt 20/20 attack; latency phải ghi đúng phạm vi đo (input layers, không phải full guard).
- Giới hạn/cách xử lý: prompt self-check gốc cho qua câu off-topic; bản sửa đầu chặn nhầm câu sạch 106 — đã làm rõ phạm vi và quy tắc tài khoản, thử 2 lượt 28/28 trước khi chạy runner, và ghi rủi ro overfit trên chính bộ 28 câu vào blueprint. Latency vượt budget được báo cáo đúng số thật. Lần chạy Phase C đầu tưởng treo do Presidio tự tải model spaCy; tải xong thì chạy lại. Đổi bottom_10 sau lần chạy Phase A đầu nên chạy lại Phase A để artifact khớp code. Với `core.autocrlf=true` trên Windows, hash SHA-256 của input JSON (CRLF) khác bản trong repo (LF), nên đã thêm `.gitattributes` (`*.json text eol=lf`), checkout lại input và chạy lại cả ba phase để metadata khớp với bản người chấm checkout.
- Nguồn hỗ trợ: mã m1–m5 từ bài Day 18 của chính mình. Mọi số liệu trong báo cáo lấy từ JSON do runner tạo trong lần chạy thật; đã đọc lại đối chiếu answer/contexts và chạy unit tests + checker để kiểm chứng.
- AI hỗ trợ: dùng Claude Code (trợ lý lập trình của Anthropic) trong VS Code.
  - Phạm vi: cài môi trường (MSVC, dependencies, Qdrant), viết code các Task 1–12 và adapter m2/m4/m5, debug NeMo input rail và chỉnh prompt self check input, phát hiện lỗi hash do CRLF/LF, soạn nháp ba báo cáo và TEAM.
  - Không dùng AI để tạo số đo hay nhãn: mọi số liệu, nhãn judge và latency đều do runner `--live` sinh ra từ API thật; báo cáo chỉ trích lại từ `artifacts/*.json`.
  - Cách kiểm chứng: chạy `python -m pytest tests/ -q` (86 passed), `python scripts/check_lab.py --with-tests` (0 failed checks), clone sạch repo từ GitHub và chạy lại checker; tự đọc answer/contexts của các câu bottom 10, các cặp judge và kết quả guard để xác nhận diễn giải trong báo cáo.

## Cập nhật sau khi nộp

Không có cập nhật sau khi nộp. Nếu sửa sau deadline sẽ ghi commit, thời điểm và lý do tại đây.

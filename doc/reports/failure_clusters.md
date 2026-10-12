# Phân tích lỗi Phase A

Nhóm: TrangPhuocHoangMinh (làm cá nhân)

Người phụ trách: Trang Phước Hoàng Minh — 2A202602690

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T15:33:27Z.
Generation mode/fallback và điều kiện chạy: cả 50 answers có `generation_mode = llm`, không có
extractive fallback. Pipeline m1–m5 từ Day 18: hierarchical chunking (child 256 ký tự), enrichment
gpt-4o-mini (contextual prepend), BM25 + BGE-M3 dense trên Qdrant v1.9.7, RRF, rerank
bge-reranker-v2-m3, top-3 contexts. Corpus: 25 file Markdown + `so_tay_an_toan.pdf` = 107 child
chunks; `BCTC.pdf` và `Nghi_dinh_so_13-2023...pdf` là PDF scan không có text layer nên bị m1 bỏ qua
(không có câu hỏi nào trong test set phụ thuộc hai file này).
Models generation/evaluator: generation `gpt-4o-mini-2024-07-18`; evaluator từ m4
`gpt-4o-mini` (LLM cho cả 4 metric) và `text-embedding-3-small` (answer_relevancy).

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0.923 | 0.511 | 0.700 |
| answer_relevancy | 0.534 | 0.391 | 0.389 |
| context_precision | 0.942 | 0.925 | 0.908 |
| context_recall | 0.900 | 0.796 | 0.717 |
| avg_score | 0.825 | 0.656 | 0.678 |

Retrieval (precision/recall) tốt hơn generation ở cả ba nhóm. Điểm thấp tập trung ở
faithfulness và answer_relevancy — tức là bước sinh câu trả lời, không phải bước tìm kiếm.

## Bottom 10 và nguyên nhân

Diagnosis/suggested_fix giữ nguyên từ Task 3 (`bottom_10`). Task 3 dùng DIAGNOSTIC_TREE theo
worst_metric, riêng câu trả lời dạng "Không tìm thấy." được tách ra: có context_recall > 0 thì
gán **over-refusal**, recall = 0 thì gán thiếu chunk (vì câu từ chối không chứa khẳng định nào nên
RAGAS cho faithfulness = 0, nhưng đó không phải hallucination).

| Rank | ID | Distribution | avg_score | worst_metric | Diagnosis (Task 3) | Suggested fix (Task 3) |
|---|---|---|---|---|---|---|
| 1 | 39 | multi_hop | 0.125 | faithfulness | Missing relevant chunks | Improve chunking or add BM25 |
| 2 | 33 | multi_hop | 0.271 | faithfulness | Over-refusal: answer 'Không tìm thấy' although retrieved contexts contain the evidence | Let the prompt answer from partial evidence and combine chunks; widen contexts (parent chunks) |
| 3 | 44 | adversarial | 0.375 | faithfulness | Over-refusal (như trên) | Như trên |
| 4 | 42 | adversarial | 0.417 | faithfulness | Over-refusal (như trên) | Như trên |
| 5 | 50 | adversarial | 0.417 | faithfulness | Over-refusal (như trên) | Như trên |
| 6 | 7 | factual | 0.419 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 7 | 25 | multi_hop | 0.458 | faithfulness | Over-refusal (như trên) | Như trên |
| 8 | 21 | multi_hop | 0.458 | answer_relevancy | Answer doesn't match question | Improve prompt template |
| 9 | 31 | multi_hop | 0.539 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 10 | 30 | multi_hop | 0.563 | answer_relevancy | Answer doesn't match question | Improve prompt template |

Câu hỏi tương ứng: 39 so sánh mật khẩu v1.0/v2.0; 33 phụ cấp + phép của Manager 12 năm;
44 chu kỳ đổi mật khẩu; 42 mốc thâm niên cộng phép; 50 VPN cá nhân khi WFH; 7 ai duyệt nghỉ không
lương 20 ngày; 25 lương thử việc Junior cao nhất; 21 phép + lương Senior 9 năm; 31 trần tiền khách
sạn công tác trong nước; 30 so sánh bảo hiểm thử việc/chính thức.

Đối chiếu answer/contexts/reference cho thấy bốn nhóm lỗi:

1. **Over-refusal ở generation (33, 44, 42, 50, 25).** 7/50 answers là "Không tìm thấy." (3 multi_hop,
   4 adversarial, 0 factual). Ví dụ câu 44: context thứ hai chứa nguyên văn "Mật khẩu phải được thay
   đổi **mỗi 120 ngày**" (context_recall = 1.0) nhưng answer vẫn là "Không tìm thấy.". System prompt
   của setup ("Trả lời CHỈ dựa trên context. Nếu không có → nói 'Không tìm thấy.'") khiến model từ
   chối khi context là các mảnh 256 ký tự, có header phiên bản và đoạn mô tả do m5 chèn vào, không
   thành một câu trả lời liền mạch.
2. **Retrieval thiếu dữ kiện cho câu so sánh (39, 21, 30).** Câu 39 cần 6 dữ kiện từ 2 phiên bản
   nhưng top-3 chỉ có độ dài v1.0 (8 ký tự), chu kỳ v2.0 (120 ngày) và đoạn "thay thế v1.0";
   thiếu độ dài 12 ký tự, 90 ngày và MFA v2.0 → recall 0.0. Câu 21 lấy 3 chunk về phép (trong đó có
   cả chunk v2023 "5 năm") mà không có chunk bảng lương, nên answer đúng phần phép (18 ngày) nhưng
   nói "Không tìm thấy thông tin về lương". Câu 30 có chunk thử việc nhưng thiếu chunk gói PVI 200
   triệu. Top-3 child chunks không đủ cho câu cần ghép hai tài liệu.
3. **Lỗi suy luận số (câu 24, avg 0.571, xếp ngay sau bottom 10 ở lần chạy cuối).** Answer tính phạt
   tạm ứng theo 20 ngày thay vì 5 ngày quá hạn sau mốc 15 ngày → 200.000 thay vì 50.000 VNĐ. Đây là
   lỗi generation thật, không phải retrieval (context_recall = 1.0).
4. **Giới hạn evaluator (7, 31).** Answer câu 7 ("Giám đốc điều hành (CEO).") và câu 31 (2.400.000 VNĐ)
   đúng với reference nhưng faithfulness = 0. Câu 7 là answer cụt không có chủ ngữ nên RAGAS khó
   tách statement; câu 31 có dòng enrichment sai ("tài liệu hướng dẫn về công tác nước ngoài" gắn
   vào chunk khách sạn trong nước), làm evaluator nghi ngờ. Hai câu này nên được người đọc lại trước
   khi coi là hallucination.

## Matrix và nhóm yếu nhất

Matrix đếm **mọi câu** theo metric thấp nhất của câu đó (tổng cột = 20/20/10 là kích thước nhóm,
không phải số lỗi):

| worst_metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 2 | 9 | 3 |
| answer_relevancy | 15 | 11 | 5 |
| context_precision | 1 | 0 | 1 |
| context_recall | 2 | 0 | 1 |

Nhóm yếu theo mean thấp nhất: multi_hop; mean: 0.656 (adversarial 0.678, factual 0.825).
Worst metric xuất hiện nhiều nhất: answer_relevancy; số câu: 31.

multi_hop yếu vì cần ghép dữ kiện từ 2 tài liệu (phép + lương, phụ cấp + phép, thử việc + bảo hiểm)
hoặc tính toán, trong khi pipeline chỉ đưa 3 child chunks 256 ký tự vào prompt. Faithfulness của
multi_hop chỉ 0.511 (9/20 câu có worst = faithfulness) vì answer hoặc từ chối hoặc tự tính toán
ngoài context. answer_relevancy thấp ở cả factual (0.534) chủ yếu do answer rất ngắn hoặc lặp lại
chính sách mà không nhắc lại đối tượng câu hỏi — metric này sinh câu hỏi ngược từ answer rồi so
embedding, nên answer cụt bị điểm thấp dù đúng; vì vậy nó là worst_metric phổ biến nhất nhưng không
phải lỗi nghiêm trọng nhất.

Đề xuất sửa và cách kiểm chứng:

- Trả về **parent chunk** (2048 ký tự) thay vì child khi đưa vào prompt (m1 đã có parent_id) và
  tăng top_k cho câu có từ "so sánh"/nhiều thực thể → kỳ vọng tăng context_recall của multi_hop.
- Sửa prompt generation: trả lời phần có bằng chứng, chỉ nói "Không tìm thấy" cho phần thiếu; ưu
  tiên phiên bản hiện hành khi context có cả bản cũ và mới → kỳ vọng giảm 7 câu từ chối.
- Bỏ dòng mô tả do m5 chèn khỏi text đưa cho LLM (chỉ dùng để embed) → giảm nhiễu cho evaluator.
- Kiểm chứng: chạy lại `python scripts/setup_answers.py --live` rồi
  `python scripts/run_experiments.py --phase a --live`, so sánh mean multi_hop (mốc 0.656), số câu
  "Không tìm thấy" (mốc 7) và faithfulness multi_hop (mốc 0.511) trên cùng test set.

## Bẫy adversarial và giới hạn

adversarial mean 0.678 < factual 0.825 (điều kiện bonus), nhưng cao hơn multi_hop 0.656. Đọc từng
câu adversarial cho thấy pipeline xử lý bẫy phiên bản **không đồng đều**:

- Đúng phiên bản: câu 41 trả 15 ngày (v2024, không lấy 12 ngày v2023), câu 43 trả 12 ký tự (v2.0),
  câu 49 hỏi rõ v2023 thì trả 12 ngày và nói thêm chính sách hiện hành. Câu 46 (phủ định: thử việc
  KHÔNG được phép năm) và 47 (không tự xử lý malware) đúng.
- Sai do từ chối thay vì chọn phiên bản: câu 42 (contexts có cả "từ 3 năm" v2024 lẫn "5 năm" v2023)
  và câu 44 (có "120 ngày" v2.0) đều trả "Không tìm thấy." — model gặp hai phiên bản mâu thuẫn và
  chọn từ chối. Câu 50 (bẫy policy contradiction VPN cá nhân) cũng từ chối thay vì trả lời "KHÔNG".
- Vì vậy điểm adversarial thấp hơn **không chứng minh** pipeline nhận ra bẫy; nó phản ánh chủ yếu
  over-refusal khi có xung đột phiên bản. Chỉ các câu 41/43/49 cho thấy chọn đúng phiên bản.

Giới hạn: chỉ 50 câu (adversarial 10 câu → mỗi câu đổi ±0.1 mean nhóm); evaluator gpt-4o-mini có
dao động — hai lần chạy Phase A trên cùng answers lệch khoảng 0.01 mean mỗi nhóm và thứ tự vài câu
cuối bottom 10 thay đổi; generation và evaluator cùng họ gpt-4o-mini nên có thể chia sẻ thiên lệch.
Không có extractive fallback trong lượt chạy này.

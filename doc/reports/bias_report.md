# Đánh giá LLM Judge Phase B

Nhóm: TrangPhuocHoangMinh (làm cá nhân)

Người phụ trách: Trang Phước Hoàng Minh — 2A202602690

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T09:02:00Z.
Models generation/judge: generation `gpt-4o-mini-2024-07-18` (nguồn answer A); judge `gpt-4o-mini`
(pairwise judge ở Task 5 và binary helper `judge_binary`, cả hai temperature 0, JSON mode).

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

Lượt 1 đưa (A, B); lượt 2 đưa (B, A) với cùng question/reference. Winner và scores lượt 2 đã được
quy về A/B gốc trước khi so sánh.

| ID | Answer A (pipeline) | Answer B (supplied) | Pass 1 | Pass 2 (quy về gốc) | Final | Consistent | Scores pass 1 (A/B) | Scores pass 2 (A/B) |
|---|---|---|---|---|---|---|---|---|
| 1 | Nghỉ 3 ngày làm việc khi kết hôn (48 ký tự) | Nghỉ 3 ngày làm việc **có lương** khi kết hôn (57) | B | B | B | true | 0.8 / 1.0 | 0.8 / 1.0 |
| 5 | Cần Tổng Giám đốc (CEO) phê duyệt (34) | Cần Giám đốc phòng ban phê duyệt (33) | A | A | A | true | 1.0 / 0.0 | 1.0 / 0.0 |
| 12 | Thưởng Tết tối thiểu cho NV chính thức từ 6 tháng là 1 tháng lương (89) | Thưởng Tết tối thiểu 1 tháng lương (50) | A | A | A | true | 1.0 / 0.6 | 1.0 / 0.8 |
| 21 | 18 ngày phép; không tìm thấy thông tin lương (91) | 18 ngày phép; lương Senior 20–35 triệu (82) | B | B | B | true | 0.7 / 1.0 | 0.7 / 1.0 |
| 41 | 15 ngày phép năm có lương (62) | 12 ngày phép năm (37) | A | A | A | true | 1.0 / 0.0 | 1.0 / 0.3 |

Reasoning chính: (1) B nêu thêm "có lương" khớp reference; (5) A đúng ngưỡng >50 triệu cần CEO, B sai
cấp duyệt; (12) A nhắc lại điều kiện 6 tháng, B thiếu điều kiện — lượt 2 thì cho điểm B 0.8 vì cả hai
cùng đúng con số; (21) B đủ cả phép lẫn lương, A thiếu lương; (41) A theo v2024 (15 ngày), B theo v2023
đã hết hiệu lực (12 ngày). Ở lượt 2 reasoning gọi tên theo vị trí đã đảo (ví dụ "Answer A" là candidate
B gốc), nhưng quyết định sau khi quy đổi trùng lượt 1 ở cả năm cặp.

Position bias count/rate: 0/5 = 0.0.
Verbosity win rate: 0.8 (4/5); decisive cases: 5 (a_wins_a_longer = 3, b_wins_b_longer = 1).

Không có cặp nào đổi winner khi đảo thứ tự, nên với mẫu này chưa thấy position bias. Verbosity 0.8
vượt ngưỡng cảnh báo 0.6, nhưng đọc nội dung thì answer dài thắng vì **đúng hơn**, không vì dài:
cặp 1 phần dài hơn chính là ý "có lương" có trong reference; cặp 41 thắng do đúng phiên bản; cặp 5
chênh 1 ký tự (34 vs 33), thắng do đúng cấp phê duyệt; cặp 21 là phản ví dụ — B ngắn hơn nhưng
thắng vì có đủ thông tin lương. Cặp 12 là trường hợp đáng nghi nhất: cả hai cùng đúng "1 tháng
lương", A chỉ lặp lại điều kiện của câu hỏi; lượt 2 thu hẹp khoảng cách (0.8 vs 0.6) cho thấy judge
dao động với cặp gần tương đương. Kết luận: chỉ số verbosity là dấu hiệu thống kê trên 5 cặp, nội
dung không cho thấy judge ưu tiên độ dài một cách có hệ thống.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| Question ID | model_answer gốc | Judge | Reasoning (tóm tắt) | Human | Agree |
|---|---|---|---|---|---|
| 1 | Nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | Chính xác, đủ ý theo reference | 1 | yes |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | >50 triệu cần CEO, không phải Giám đốc phòng ban | 0 | yes |
| 12 | Thưởng Tết tối thiểu 1 tháng lương. | 1 | Đúng mức thưởng theo reference | 1 | yes |
| 21 | 18 ngày phép (15 + 3); lương Senior 20–35 triệu. | 1 | Đúng số phép và khoảng lương | 1 | yes |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | Đúng số tiền và lý do | 1 | yes |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | Thiếu Kế toán trưởng; phạt phải tính cho 15 ngày quá hạn | 0 | yes |
| 33 | Phép 19 ngày. Phụ cấp 1.500.000 VNĐ/tháng. | 1 | Đúng cả số phép và phụ cấp | 1 | yes |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | Dùng v2023 cũ, v2024 là 15 ngày | 0 | yes |
| 46 | Thử việc không được phép năm, phải xin nghỉ không lương. | 1 | Đúng phủ định và hành động thay thế | 1 | yes |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | VPN cá nhân bị cấm, phải dùng VPN công ty | 0 | yes |

Cohen’s κ: 1.0.
Observed/chance agreement và diễn giải: p_o = 10/10 = 1.0. Judge và human đều có 6 nhãn 1 và 4 nhãn
0, nên p_e = 0.6 × 0.6 + 0.4 × 0.4 = 0.52; κ = (1.0 − 0.52) / (1 − 0.52) = 1.0 — "almost perfect"
theo Landis-Koch, vượt mốc 0.6. Reasoning của judge trùng ý với human_note ở các câu sai (5, 29,
41, 50): sai cấp duyệt, thiếu điều kiện, dùng phiên bản cũ, vi phạm chính sách.

## Giới hạn và cách dùng judge

- Mẫu rất nhỏ: 5 cặp pairwise và 10 nhãn binary. κ = 1.0 trên 10 câu có khoảng tin cậy rộng; chỉ
  một câu lệch (ví dụ judge 1, human 0) sẽ kéo κ xuống khoảng 0.78. Không suy ra judge luôn đúng.
- Các câu sai trong bộ nhãn là lỗi "rõ" (sai con số, sai phiên bản, sai cấp duyệt) và reference
  chứa đáp án tường minh; judge chưa được thử với câu đúng một phần hoặc diễn đạt mơ hồ.
- Judge (gpt-4o-mini) cùng họ model với generation và evaluator, nên có thể cùng điểm mù; nên kiểm
  tra chéo bằng một model khác hoặc người đọc mẫu ngẫu nhiên.
- Scores trong pairwise dao động giữa hai lượt (cặp 12: B 0.6 → 0.8; cặp 41: B 0.0 → 0.3) dù winner
  không đổi; chỉ dùng winner sau swap-and-average, không dùng scores một lượt làm thước đo tuyệt đối.
- Cách dùng đề xuất: judge là bộ lọc tự động trong CI, kèm định kỳ lấy mẫu để người gán nhãn lại và
  tính lại κ; nếu κ < 0.6 thì dừng dùng judge làm gate cho tới khi sửa prompt.

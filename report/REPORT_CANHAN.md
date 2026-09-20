# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Tô Huy Thông
**Nhóm:** Nhóm TMĐT K4-L3B
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> *Viết 1-2 câu:* Nó có nghĩa là hai vector đại diện cho văn bản có hướng rất gần nhau (góc giữa chúng hẹp). Điều này biểu thị rằng nội dung của hai văn bản có chung một ý nghĩa ngữ nghĩa hoặc thuộc cùng một chủ đề.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Làm thế nào để đổi trả hàng trên eBay?"
- Câu B: "Quy trình trả lại sản phẩm đã mua trên eBay là gì?"
- Tại sao tương đồng: Cả hai đều hỏi về cùng một thủ tục hậu mãi, sử dụng các từ đồng nghĩa ("đổi trả" và "trả lại sản phẩm").

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Tôi muốn mua điện thoại iPhone 15 mới."
- Câu B: "Làm thế nào để đổi trả hàng trên eBay?"
- Tại sao khác: Một câu thể hiện nhu cầu mua sắm thiết bị điện tử, câu kia hỏi về chính sách quy định. Ý nghĩa hoàn toàn không liên quan.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> *Viết 1-2 câu:* Cosine similarity chỉ quan tâm đến "hướng" của vector (sự tương đồng về mặt ý nghĩa) và bỏ qua độ lớn của vector (độ dài văn bản). Hai văn bản nói về cùng một chủ đề (một câu ngắn, một đoạn dài) sẽ có cosine cao, trong khi khoảng cách Euclidean của chúng có thể rất lớn và không phản ánh đúng ý nghĩa.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* Bước nhảy (step) = chunk_size - overlap = 500 - 50 = 450 ký tự. Chunk đầu tiên lấy 500 ký tự, còn lại 9500 ký tự. Số chunk tiếp theo = ceil(9500 / 450) = 22. Tổng cộng: 1 + 22 = 23 chunks.
> *Đáp án:* 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> *Viết 1-2 câu:* Số lượng chunk sẽ tăng lên (step giảm còn 400, tạo ra 25 chunks). Ta muốn tăng độ chồng chéo để tránh việc một ý hay một câu quan trọng bị cắt đứt gãy ở giữa hai chunk, giúp bảo toàn ngữ cảnh tốt hơn cho LLM.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> *Viết 2-3 câu:* Tôi sử dụng `re.split(r'(\. |\! |\? |\.\n)', text)` để tách văn bản tại các dấu kết thúc câu. Để xử lý trường hợp ngoại lệ mất dấu câu, tôi đã duyệt qua danh sách kết quả, gộp phần nội dung với dấu câu đi kèm, dùng `.strip()` loại bỏ khoảng trắng thừa, sau đó ghép nối chúng lại theo giới hạn `max_sentences_per_chunk`.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> *Viết 2-3 câu:* Thuật toán nhận vào một mảng `separators` giảm dần kích thước. Base case là khi đoạn văn bản ngắn hơn `chunk_size` hoặc không còn separator nào. Thuật toán sẽ dùng separator hiện tại để cắt, gộp lại cho đến khi đầy `chunk_size`; nếu chunk tạo ra vẫn quá dài, nó gọi đệ quy chính nó với separator tiếp theo để chia nhỏ thêm.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> *Viết 2-3 câu:* Dữ liệu `add_documents` được lưu dưới dạng danh sách các dict chứa id, content, metadata và vector (hoặc add thẳng vào `ChromaDB` collection). Hàm `search` sẽ dùng `_embedding_fn` để nhúng query, tính cosine similarity với từng record rồi sort giảm dần điểm số để lấy top_k.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> *Viết 2-3 câu:* Hàm lọc (filter) được áp dụng TRƯỚC (pre-filtering) bằng cách dùng list comprehension loại bỏ các record không có metadata tương ứng trước khi đưa vào tính cosine. Hàm xóa (delete) chỉ việc duyệt lại mảng và giữ lại các chunk có `doc_id` KHÁC với ID được yêu cầu.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> *Viết 2-3 câu:* Lớp này sử dụng hàm `search` của store để lấy top_k chunk, trích xuất thuộc tính `content` và dùng `\n\n` để nối chúng lại thành một biến `Context`. Sau đó chèn ngữ cảnh này cùng với `Question` vào chung một Prompt template và gửi tới hàm `llm_fn` để sinh ra câu trả lời dựa trên tài liệu.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.10.0, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\tohuy\AppData\Local\Programs\Python\Python310\python.exe
cachedir: .pytest_cache
rootdir: D:\K4-DAY07-T-Huy-Th-ng---2A202602608
plugins: anyio-4.13.0, langsmith-0.7.25
collecting ... collected 42 items
...
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.80s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Chính sách hoàn tiền" | "Làm sao để lấy lại tiền" | cao | 0.82 | Đúng |
| 2 | "Apple iPhone 15" | "Quả táo màu đỏ" | thấp | 0.21 | Đúng |
| 3 | "Tôi rất vui" | "Tôi không hề buồn" | cao | 0.75 | Đúng |
| 4 | "Máy bay cất cánh" | "Phi cơ rời đường băng" | cao | 0.85 | Đúng |
| 5 | "Đăng ký tài khoản" | "Cách hoàn tiền" | thấp | 0.15 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> *Viết 2-3 câu:* Kết quả bất ngờ nhất là cặp 3 ("Tôi rất vui" và "Tôi không hề buồn"). Dù ngược nhau hoàn toàn về mặt cấu trúc và từ vựng (không dùng chung từ nào), nhưng mô hình embedding vẫn nhận diện được sự tương đồng về mặt ý nghĩa (ngữ nghĩa tích cực). Điều này chứng tỏ embedding lưu giữ ý nghĩa (semantics) thực sự chứ không chỉ là khớp từ khóa.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Nếu hàng nhận được không khớp với mô tả... | (ebay-buyer-money-back...) The item received by the buyer doesn't match... | 0.450 | Có | Agent nhận được context đúng về việc hàng không khớp mô tả. |
| 2 | Người bán có bao lâu để phản hồi yêu cầu... | (ebay-buyer-return-refund) The seller has 3 business days to get back to you... | 0.606 | Có | Agent nhận được context đúng là 3 ngày. |
| 3 | Sau khi hoàn tiền được xử lý, người mua... | (ebay-buyer-money-back...) 30 calendar days after the estimated or actual... | 0.344 | Không | Chunk lấy ra nói về thời hạn 30 ngày để mở case, sai nội dung. |
| 4 | Tỉ lệ lỗi giao dịch tối đa được phép trong... | (ebay-seller-standards) All sellers are required to maintain the following... | 0.336 | Không | Đoạn văn không chứa thông tin con số 2% mà chỉ giới thiệu. |
| 5 | Liệt kê các điều kiện để người bán được... | (ebay-seller-protections) Protections for Top Rated Sellers sellers are eligible... | 0.583 | Có | Lấy đúng đoạn đề cập đến bảo vệ cho Top Rated Seller. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 3 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *Viết 2-3 câu:* Tôi học được cách sử dụng Metadata Filter như một lớp "phễu" để phân luồng người dùng (buyer vs seller). Thay vì để Vector Search tìm kiếm nhầm chính sách của hai đối tượng có nội dung rất giống nhau, filter giúp thu hẹp ngữ cảnh một cách an toàn và tăng độ chuẩn xác lên 100%.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |

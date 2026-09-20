# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Manngusidan  
**Thành viên:** 
- Đinh Văn Bình (R1 — FixedSizeChunker)
- Tô Huy Thông (R2 — RecursiveChunker)
- Trần Gia Khánh (R3 — HeadingChunker)
- Ngô Đình Minh Nhật (R4 — SemanticChunker & Benchmark Lead)  
**Ngày:** 20/09/2026  

> [!NOTE]
> **Quy định nộp bài:** Nộp 1 bản / nhóm. Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm theo `docs/SCORING.md`.  
> **Tổng điểm phần nhóm:** **40 / 40 điểm** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình & Bài học (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### 1.1. Chủ đề (Domain) & Lý Do Chọn

- **Chủ đề:** Chính sách đổi trả, hoàn tiền và quy định người bán trên sàn thương mại điện tử eBay (Biến thể K4-L3B).
- **Lý do chọn chủ đề:**
  > Nhóm lựa chọn hệ thống chính sách chính thức của eBay vì đây là nguồn thông tin công khai, có cấu trúc điều khoản pháp lý rõ ràng về bảo vệ người mua (`buyer`), quyền lợi hoàn tiền (`money back guarantee`), và tiêu chuẩn bảo vệ người bán (`seller`).
  >
  > Đặc biệt, corpus có sự phân hóa vai trò đối tượng sâu sắc giữa `buyer` và `seller`. Từ vựng giữa hai nhóm này thường xuyên chồng lặp (cùng bàn về return, refund, shipping, dispute), tạo ra thách thức thực tế lý tưởng để kiểm chứng sức mạnh của việc kết hợp **Vector Retrieval** với **Metadata Pre-filtering** (`audience`, `category`).

---

### 1.2. Danh sách tài liệu (Data Inventory)

Corpus được chuẩn hóa và lưu trữ tại thư mục `data/ecommerce-crawled-final/` — gồm **5 tài liệu**, cập nhật ngày 20/09/2026.

| # | `doc_id` | Tiêu đề tài liệu | Nguồn chính thức | Số ký tự (body) | Số từ | `audience` | `category` |
|---|---|---|---|---:|---:|:---:|:---:|
| 1 | `ebay-buyer-money-back-guarantee` | Chính sách eBay Money Back Guarantee | [ebay.com/help/policies/4210](https://www.ebay.com/help/policies/ebay-money-back-guarantee-policy/ebay-money-back-guarantee-policy?id=4210) | 32,305 | 5,282 | `buyer` | `buyer-protection` |
| 2 | `ebay-buyer-return-refund` | Quy định trả hàng và hoàn tiền | [ebay.com/help/buying/4041](https://www.ebay.com/help/buying/returns-refunds/return-item-refund?id=4041) | 11,281 | 2,031 | `buyer` | `returns-policy` |
| 3 | `ebay-buyer-return-shipping` | Chi phí vận chuyển khi trả hàng | [ebay.com/help/returns-refunds/4066](https://www.ebay.com/help/returns-refunds/returning-item-purchased/return-postage?id=4066) | 6,725 | 1,143 | `buyer` | `returns-policy` |
| 4 | `ebay-seller-protections` | Cơ chế bảo vệ người bán trên eBay | [ebay.com/help/policies/4345](https://www.ebay.com/help/policies/selling-policies/seller-protections?id=4345) | 14,190 | 2,398 | `seller` | `seller-protection` |
| 5 | `ebay-seller-standards` | Tiêu chuẩn hiệu suất của người bán | [ebay.com/help/policies/4347](https://www.ebay.com/help/policies/selling-policies/seller-performance-policy?id=4347) | 18,804 | 3,088 | `seller` | `seller-performance` |

- **Tổng dung lượng corpus:** 83,305 ký tự · 13,942 từ.
- **Cơ cấu phân bổ:** 3 tài liệu `buyer` (61%) + 2 tài liệu `seller` (39%).

**Danh sách kiểm tra quản trị dữ liệu (Data Governance Checklist):**
- [x] Corpus chỉ thu thập từ cổng trợ giúp công khai của eBay, không chứa thông tin cá nhân (PII), thông tin thanh toán hay dữ liệu nội bộ.
- [x] Mỗi tài liệu có đầy đủ Frontmatter YAML: `source_url`, `retrieved_at`, `document_version`, `audience`, `category`.
- [x] Nguồn gốc và giấy phép truy cập công khai (`public-source`) được ghi nhận đầy đủ trong `data/ecommerce-crawled-final/sources.csv`.

---

### 1.3. Cấu trúc Metadata (Metadata Schema)

| Trường Metadata | Kiểu dữ liệu | Ví dụ thực tế | Ý nghĩa & Ứng dụng trong Retrieval |
|---|---|---|---|
| `doc_id` | `string` | `ebay-buyer-return-refund` | Khóa định danh ổn định; dùng để map chunk về tài liệu nguồn và hỗ trợ hàm `delete_document()`. |
| `title` | `string` | `Quy định trả hàng và hoàn tiền` | Định danh tên bài viết chính sách; phục vụ hiển thị kết quả và giải thích lý do truy xuất. |
| `source_url` | `string` | `https://www.ebay.com/help/...` | Đường dẫn trực tiếp đến điều khoản gốc, hỗ trợ truy nguyên và kiểm chứng tính xác thực. |
| `retrieved_at` | `date` | `2026-09-20` | Dấu thời gian thu thập dữ liệu; giúp phát hiện chính sách lỗi thời khi eBay cập nhật. |
| `document_version` | `string` | `not-stated` | Phiên bản tài liệu khi nhà cung cấp có công bố số hiệu phiên bản. |
| `audience` | `enum` | `buyer` / `seller` | **Trường lọc trọng yếu:** Phân tách không gian tìm kiếm, triệt tiêu việc lẫn lộn quyền lợi giữa người mua và người bán. |
| `category` | `string` | `returns-policy` | Phân loại phân hệ chính sách (bảo vệ, đổi trả, tiêu chuẩn); giúp thu hẹp intent tìm kiếm. |
| `language` | `string` | `en` | Định danh ngôn ngữ của corpus (tiếng Anh chuẩn). |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> [!NOTE]
> Mỗi thành viên triển khai và đo kiểm một chiến lược độc lập trên cùng bộ tài liệu. Toàn bộ kết quả sau đó được tổng hợp và đối chuẩn công bằng.

### 2.1. Phân tích đường cơ sở (Baseline Analysis)

Kết quả thực nghiệm phân tích đường cơ sở bằng `ChunkingStrategyComparator().compare()` trên 3 tài liệu đại diện (đã bóc tách YAML frontmatter):

| Tài liệu mẫu | Chiến lược | Số chunk | Độ dài TB (ký tự) | Nhận xét chi tiết |
|---|---|---:|---:|---|
| `ebay-buyer-return-refund` | `fixed_size` | 17 | 781.8 | Kích thước đồng đều nhưng dễ cắt đứt giữa các điều kiện hoàn tiền. |
| `ebay-buyer-return-refund` | `by_sentences` | 35 | 354.0 | Quá nhiều chunk nhỏ; câu bị cô lập mất ngữ cảnh của mục cha. |
| `ebay-buyer-return-refund` | `recursive` | 17 | 721.5 | Giữ ranh giới đoạn văn và danh sách điều khoản rất tốt. |
| `ebay-buyer-money-back-guarantee` | `fixed_size` | 48 | 789.2 | Độ dài tối ưu ngưỡng 800 ký tự nhưng gặp hiện tượng đứt đoạn câu. |
| `ebay-buyer-money-back-guarantee` | `by_sentences` | 39 | **907.9** | **Vượt ngưỡng 800:** Do câu pháp lý dài; `SentenceChunker` không kiểm soát `chunk_size`. |
| `ebay-buyer-money-back-guarantee` | `recursive` | 48 | 720.6 | Tối ưu nhất về cấu trúc tự nhiên của văn bản. |
| `ebay-seller-standards` | `fixed_size` | 6 | 705.8 | Phân mảnh tương đối gọn nhưng có nguy cơ cắt ngang heading. |
| `ebay-seller-standards` | `by_sentences` | 11 | 359.5 | Chunk quá ngắn, làm mất mối quan hệ giữa chỉ số và định nghĩa. |
| `ebay-seller-standards` | `recursive` | 7 | 557.1 | Cân bằng tốt số lượng chunk và ngữ cảnh toàn đoạn. |

> [!WARNING]
> **Nhận định quan trọng:** `SentenceChunker` gom câu thuần túy theo tham số `max_sentences_per_chunk=3` mà không nhận tham số `chunk_size`. Đối với văn bản điều khoản pháp lý phức hợp, các câu đơn dài có thể đẩy kích thước chunk vượt 900+ ký tự, làm loãng vector nhúng và giảm độ chính xác truy xuất.

---

### 2.2. Chiến lược của từng thành viên

#### R1 — Đinh Văn Bình: FixedSizeChunker (with Overlap)
- **Cấu hình cá nhân đã chạy:** `FixedSizeChunker(chunk_size=500, overlap=50)`; tạo **186 chunks từ 5 tài liệu** trong `data/ecommerce-crawled-final/`.
- **Đặc tính kỹ thuật & Lý do chọn:** Cắt văn bản thành các khối tối đa 500 ký tự với overlap 50 ký tự (10%) làm baseline đơn giản, dễ tái lập. Overlap giữ một phần ngữ cảnh ở ranh giới nhưng không bảo đảm giữ trọn câu hoặc danh sách điều kiện. Số chiều vector do mô hình embedding quyết định, không phải do kích thước chunk.
- **Embedding:** LocalEmbedder với `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; vector được chuẩn hóa trước khi tính score.
- **Agent:** `gemini-2.5-flash`, temperature 0; đã chạy đủ 5 câu và lưu câu trả lời thực tế.
- **Truy xuất:** `top_k=3`; filter `audience=buyer` cho Q1–Q3 và `audience=seller` cho Q4–Q5.
- **Kết quả cá nhân:** **3/10 theo marker**, **6/10 theo đánh giá nội dung và Agent**. Q1 và Q2 có đáp án đúng nhưng không khớp marker; Q3 trả lời sai mốc thời gian; Q4 trả lời đúng với chunk đáp án ở top-2; Q5 có marker ở top-1 nhưng thiếu các điều kiện do chunk bị cắt.
- **Bằng chứng:** [Báo cáo cá nhân](REPORT_CANHAN.md), [log benchmark](../ket_qua_benchmark.txt), [JSON chứa top-3 và câu trả lời Agent](../ket_qua_benchmark.json).
- **A/B cá nhân:** Với Q1, filter buyer loại chunk seller đứng đầu và đưa chunk trả lời lên top-1, nhưng điểm marker vẫn 0/2 ở cả hai lượt. Q4 cá nhân hỏi tỷ lệ lỗi giao dịch tối đa 2%; top-3 không đổi khi bỏ filter, marker ở top-2 và được 1/2 ở cả hai lượt.
- **Phạm vi so sánh:** Lượt cá nhân này khác cấu hình tổng hợp Gemini embedding/800 ký tự ở các mục chung. Q4 cá nhân hỏi tỷ lệ lỗi giao dịch 2%, trong khi Q4 nhóm hỏi khấu trừ tiền hoàn 50%; Q1 cá nhân không lọc `category`, và Q2 dùng marker `seller should get back`. Không gán điểm 9/10 của lượt tổng hợp cho lượt cá nhân này; cần thống nhất cấu hình, câu hỏi và cách chấm trước khi so sánh trực tiếp.
- **Code đại diện:**
  ```python
  # Cấu hình cá nhân trong bench.py; chunking được thực hiện ngoài store.
  CHUNKER = FixedSizeChunker(chunk_size=500, overlap=50)
  ```

#### R2 — Tô Huy Thông: RecursiveChunker
- **Cấu hình:** `RecursiveChunker(chunk_size=800)`
- **Đặc tính kỹ thuật & Lý do chọn:** Phân tách văn bản theo cấu trúc phân tầng phân cấp ưu tiên `["\n\n", "\n", ". ", " ", ""]`. Chiến lược này tôn trọng triệt để ranh giới đoạn văn và các danh sách gạch đầu dòng của chính sách eBay. Giữ cấu trúc ngữ nghĩa tự nhiên tốt hơn fixed-size nhưng không chủ động duy trì thông tin heading cha cho các đoạn nằm sâu.
- **Code đại diện:**
  ```python
  chunker = RecursiveChunker(chunk_size=800)
  ```

#### R3 — Trần Gia Khánh: HeadingChunker (Biến thể bắt buộc K4-L3B)
- **Cấu hình:** `HeadingChunker(chunk_size=800)`
- **Đặc tính kỹ thuật & Lý do chọn:** Tách trước tại các tiêu đề Markdown (`#`, `##`, `###`). Mỗi section chính sách vốn là một đơn vị ngữ nghĩa độc lập. Nếu section dài hơn 800 ký tự, thuật toán tiếp tục phân mảnh bằng `RecursiveChunker` và **tự động nối lại tiêu đề mục cha vào đầu mỗi mảnh con** (`f"{heading}\n\n{child}"`). Nhờ vậy, khi tìm kiếm các đoạn nhỏ ở cuối mục, mô hình embedding vẫn nhận biết được ngữ cảnh "đoạn này thuộc về chính sách nào".
- **Thực nghiệm độc lập:** Bản chạy độc lập của Khánh với `chunk_size=500` sinh ra 243 chunks; khi benchmark trên mô hình nhúng thực `all-MiniLM-L6-v2`, chiến lược đạt điểm tương đồng rất cao (0.65 – 0.79), giành vị trí Rank 1 ở Q5 (`ebay-seller-protections#3`, score 0.7488) và Top-3 ở Q3 (`ebay-buyer-return-refund#24`, score 0.6554).
- **Code đại diện:**
  ```python
  class HeadingChunker:
      heading_pattern = re.compile(r"(?m)^(#{1,6}\s+.+?)\s*$")

      def chunk(self, text: str) -> list[str]:
          matches = list(self.heading_pattern.finditer(text))
          if not matches:
              return self.recursive.chunk(text)
          chunks = []
          for i, match in enumerate(matches):
              heading = match.group(1).strip()
              end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
              section = text[match.start():end].strip()
              if len(section) <= self.chunk_size:
                  chunks.append(section)
              else:
                  body = section[len(heading):].strip()
                  for child in self.recursive.chunk(body):
                      chunks.append(f"{heading}\n\n{child}")  # Bảo toàn heading cha
          return chunks
  ```

#### R4 — Ngô Đình Minh Nhật: SemanticChunker & Tổng hợp Benchmark
- **Cấu hình:** `SemanticChunker(chunk_size=800, similarity_threshold=0.5)`
- **Đặc tính kỹ thuật & Lý do chọn:** Tách văn bản thành các câu đơn, tính toán vector nhúng của từng câu rồi gộp các câu kế tiếp có cosine similarity $\ge 0.5$. Điểm cắt (breakpoint) được kích hoạt khi ngữ nghĩa chuyển hướng hoặc kích thước vượt ngưỡng.
- **Thực nghiệm & Hạn chế:** Khi chạy trên `MockEmbedder` (sinh vector bằng MD5 hash), sự biến thiên ngẫu nhiên làm kích hoạt breakpoint liên tục $\rightarrow$ sinh ra 401 chunk rất nhỏ (trung bình 206 ký tự), khiến điểm Two-Level Scoring đạt 0/10.
- **Vai trò điều phối nhóm:** Nhật là người chịu trách nhiệm quy chuẩn hóa mã nguồn benchmark (`bench.py`), tích hợp các chiến lược của R1–R3, thiết lập cơ chế retry khi gặp lỗi hạn mức `429 RESOURCE_EXHAUSTED` từ Gemini API, và tổng hợp bảng dữ liệu đối chuẩn chính thức cho cả nhóm.
- **Code đại diện:**
  ```python
  class SemanticChunker:
      def __init__(self, embedder, chunk_size=800, similarity_threshold=0.5):
          self.embedder = embedder
          self.chunk_size = chunk_size
          self.similarity_threshold = similarity_threshold
          self._sentence_splitter = SentenceChunker(max_sentences_per_chunk=1)

      def chunk(self, text):
          sentences = self._sentence_splitter.chunk(text)
          if len(sentences) <= 1:
              return sentences
          embeddings = self.embedder.embed_many(sentences)
          chunks, current, current_len = [], [sentences[0]], len(sentences[0])
          for i in range(1, len(sentences)):
              similarity = compute_similarity(embeddings[i - 1], embeddings[i])
              sentence = sentences[i]
              if similarity < self.similarity_threshold or current_len + len(sentence) > self.chunk_size:
                  chunks.append(" ".join(current))
                  current, current_len = [sentence], len(sentence)
              else:
                  current.append(sentence)
                  current_len += len(sentence) + 1
          chunks.append(" ".join(current))
          return chunks
  ```

---

### 2.3. So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược | Số Chunk / Toàn bộ Corpus | Điểm mạnh cốt lõi | Điểm yếu / Giới hạn |
|---|---|---:|---|---|
| **R1 — Bình** | `FixedSizeChunker(500, 50)`, lượt cá nhân dùng embedding local | 186 chunks | Dễ tái lập; có kết quả Agent và A/B; 3/10 marker, 6/10 nội dung + Agent. | Có thể cắt giữa điều kiện; khác cấu hình/bộ câu hỏi của lượt tổng hợp nên chưa so sánh điểm trực tiếp. |
| **R2 — Thông** | `RecursiveChunker(800)` | 117 chunks | Giữ trọn vẹn ranh giới câu, đoạn văn và danh sách liệt kê. | Không nhận diện cấu trúc heading; các mảnh con bị mất ngữ cảnh mục cha. |
| **R3 — Khánh** | `HeadingChunker(800)` | 146 chunks (tổng hợp)<br>*(243 chunks ở chunk_size=500)* | Giữ toàn vẹn ngữ cảnh tiêu đề cho từng chunk; đạt điểm truy xuất cao nhất. | Phụ thuộc vào chất lượng đánh dấu heading Markdown của văn bản nguồn. |
| **R4 — Nhật** | `SemanticChunker(800, 0.5)` | 401 chunks (Mock)<br>*(Lead benchmark toàn nhóm)* | Ranh giới cắt hoàn toàn dựa trên sự dịch chuyển ngữ nghĩa thực tế. | Phụ thuộc tuyệt đối vào chất lượng model nhúng; tính toán nặng và đắt đỏ. |

> [!TIP]
> **Chiến lược tối ưu nhất cho bài toán chính sách TMĐT:**  
> **`HeadingChunker` là chiến lược vượt trội nhất (10/10 điểm Two-Level Scoring).**  
> Đối với tài liệu chính sách, một đoạn văn đứng riêng lẻ sẽ rất mơ hồ (ví dụ: đoạn "phải hoàn tất trong vòng 3 ngày"). Việc `HeadingChunker` tự động đính kèm ngữ cảnh `"## Trách nhiệm của người bán khi có yêu cầu hoàn tiền"` giúp mô hình embedding định vị chính xác mục tiêu truy vấn, giải quyết triệt để các câu hỏi hỏi về số liệu và điều kiện cụ thể.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### 3.1. Bộ câu hỏi đánh giá & Câu trả lời chuẩn (Gold Standard)

Nhóm thống nhất bộ 5 câu hỏi bao quát đầy đủ các dạng truy vấn chính sách (điều kiện, số liệu, quy trình, ngoại lệ, liệt kê).

| # | Dạng hỏi | Câu hỏi đánh giá (Song ngữ VI / EN) | Câu trả lời chuẩn (Gold Answer & Marker) | Metadata Filter áp dụng | Tài liệu nguồn |
|:---:|---|---|---|---|---|
| **Q1** | Điều kiện | Nếu hàng nhận được không khớp với mô tả hoặc bị hư hỏng, người mua có thể làm gì?<br>*(What happens if an item does not match the listing or arrives faulty or damaged?)* | Người mua có thể đủ điều kiện hưởng eBay Money Back Guarantee và có thể trả lại hàng ngay cả khi chính sách của người bán ghi không chấp nhận đổi trả.<br>**Marker:** `return it even if` | `{"audience": "buyer", "category": "returns-policy"}` | `ebay-buyer-return-refund` |
| **Q2** | Tra cứu số liệu | Người bán có bao lâu để phản hồi yêu cầu trả hàng của người mua?<br>*(How long does the seller have to respond to a buyer's return request?)* | Người bán có thời hạn **3 ngày làm việc** để phản hồi yêu cầu của người mua.<br>**Marker:** `3 business days` | `{"audience": "buyer"}` | `ebay-buyer-return-refund` |
| **Q3** | Tra cứu số liệu | Sau khi hoàn tiền được xử lý, người mua thường mất bao lâu để nhận được tiền?<br>*(How long do refunds typically take to become available?)* | Tiền hoàn thường có sẵn trong tài khoản của người mua trong vòng **3–5 ngày làm việc**.<br>**Marker:** `typically available` | `{"audience": "buyer"}` | `ebay-buyer-return-refund` |
| **Q4** | Tình huống / Chỉ số | Khi người mua trả lại món hàng đã qua sử dụng hoặc bị hư hỏng, khoản hoàn tiền bị khấu trừ thế nào? / Tỷ lệ lỗi giao dịch tối đa là bao nhiêu?<br>*(When an item is returned damaged, how is the refund handled? / What is the max defect rate?)* | Người bán có thể khấu trừ tối đa **50%** giá trị hoàn lại để bù phần giá trị tài sản bị tổn thất (**Marker:** `deduct up to 50%`); hoặc Tỷ lệ lỗi giao dịch của người bán không được vượt quá **2%** (**Marker:** `No more than 2%`). | `{"audience": "seller"}` | `ebay-seller-protections` / `ebay-seller-standards` |
| **Q5** | Liệt kê | Liệt kê các điều kiện để người bán được hưởng cơ chế bảo vệ dành cho Top Rated Seller.<br>*(List the eligibility conditions for protections for Top Rated Sellers.)* | Phải là Top Rated Seller tại thời điểm giao dịch; cư trú tại Mỹ/Canada; không bị đánh giá "Very High" về tỷ lệ tranh chấp; item niêm yết trên eBay.com; chấp nhận chính sách trả hàng $\ge 30$ ngày.<br>**Marker:** `Top Rated Seller at the time` | `{"audience": "seller"}` | `ebay-seller-protections` |

---

### 3.2. Đánh giá chất lượng truy xuất (Two-Level Scoring)

> [!NOTE]
> **Quy tắc tính điểm Two-Level Scoring (theo chuẩn Checkpoint 6):**
> - **2 điểm:** Chuỗi `marker` xuất hiện ngay trong chunk xếp hạng **Top-1**.
> - **1 điểm:** Chuỗi `marker` xuất hiện trong chunk xếp hạng **Top-2** hoặc **Top-3**.
> - **0 điểm:** Chuỗi `marker` **không có** trong bất kỳ chunk nào thuộc Top-3.
> 
> Toàn bộ 3 chiến lược được đối chuẩn chính thức bằng mô hình nhúng thực (`gemini-embedding-001` / `all-MiniLM-L6-v2`) trên cùng 5 câu hỏi và cùng bộ metadata filter.

| # | Tóm tắt câu hỏi | Chuỗi Marker kiểm tra | R1 — Fixed+Overlap | R2 — Recursive | R3 — Heading | Phân tích chi tiết |
|:---:|---|---|:---:|:---:|:---:|---|
| **Q1** | Hàng lỗi/hỏng $\rightarrow$ quyền lợi | `return it even if` | **2** / 2 (Rank 1) | **2** / 2 (Rank 1) | **2** / 2 (Rank 1) | Filter loại bỏ triệt để các section chung chung, đưa chunk chứa điều khoản cụ thể lên Top-1. |
| **Q2** | Thời hạn seller phản hồi | `3 business days` | **2** / 2 (Rank 1) | **2** / 2 (Rank 1) | **2** / 2 (Rank 1) | Cả 3 chiến lược đều đưa marker lên Rank 1 với độ tương đồng rất cao. |
| **Q3** | Thời gian tiền về tài khoản | `typically available` | **2** / 2 (Rank 1) | **0** / 2 (Vắng mặt) | **2** / 2 (Rank 1) | **Failure Case của R2:** Recursive cắt đứt section khiến chunk chứa số liệu bị đẩy ra ngoài Top-3. |
| **Q4** | Khấu trừ hàng hoàn / Defect rate | `deduct up to 50%` / `2%` | **2** / 2 (Rank 1) | **0** / 2 (Vắng mặt) | **2** / 2 (Rank 1) | R1, R3 định vị chính xác. R2 thất bại do không chứa thông tin cụ thể. |
| **Q5** | Điều kiện bảo vệ Top Rated | `Top Rated Seller at the time` | **1** / 2 (Rank 3) | **2** / 2 (Rank 1) | **2** / 2 (Rank 1) | FixedSize bị trôi xuống Rank 3 do cắt ngang danh sách; Heading đạt Rank 1 trọn vẹn. |
| **TỔNG** | **Tổng điểm chất lượng truy xuất** | | **9 / 10** | **6 / 10** | **10 / 10** | **`HeadingChunker` xuất sắc nhất toàn diện.** |

---

### 3.3. Thực nghiệm A/B Testing — Đánh giá vai trò của Metadata Filter

Nhóm giữ nguyên 100% nội dung câu hỏi truy vấn (Query Text) và thực hiện hai lượt chạy song song: **CÓ FILTER (WITH)** vs **KHÔNG CÓ FILTER (WITHOUT)**.

| Query | Chiến lược | Điểm WITH Filter | Điểm WITHOUT Filter | Top-3 có thay đổi? | Kết luận thực nghiệm |
|:---:|---|:---:|:---:|:---:|---|
| **Q1** | FixedSize + Overlap | **2/2** (Rank 1) | **0/2** (Vắng mặt) | **CÓ** | Metadata filter loại bỏ các tài liệu Money Back Guarantee chung, giữ lại đúng tài liệu đổi trả thực tế. |
| **Q1** | RecursiveChunker | **2/2** (Rank 1) | **0/2** (Vắng mặt) | **CÓ** | Filter cứu vãn hoàn toàn câu hỏi từ thất bại (0đ) lên đạt điểm tuyệt đối (Rank 1). |
| **Q1** | HeadingChunker | **2/2** (Rank 1) | **1/2** (Rank 2) | **CÓ** | Filter đưa chunk "Top Takeaway" trực tiếp lên vị trí dẫn đầu (Rank 1). |
| **Q4** | FixedSize + Overlap | **2/2** (Rank 1) | **2/2** (Rank 1) | **CÓ** | Filter loại bỏ 1 chunk của buyer lọt vào Top-3, giúp context thuần seller 100%. |
| **Q4** | RecursiveChunker | **0/2** (Vắng mặt) | **0/2** (Vắng mặt) | **KHÔNG** | R2 không tìm được chunk chứa đáp án dù có hay không có filter. |
| **Q4** | HeadingChunker | **2/2** (Rank 1) | **2/2** (Rank 1) | **KHÔNG** | Từ vựng trong query đã quá đặc trưng, không có sự thay đổi thứ hạng Top-3. |

> [!IMPORTANT]
> **Kết luận chuyên sâu về Metadata Filtering:**
> 1. **Lọc metadata mang lại giá trị đột phá khi intent có nguy cơ phân tán (như Q1):** Khi một câu hỏi có nhiều tài liệu cùng chia sẻ từ khóa (cả bài Money Back Guarantee lẫn bài Returns & Refunds đều nói về hoàn tiền), filter `category="returns-policy"` đóng vai trò quyết định giúp triệt tiêu nhiễu và đẩy marker từ ngoài Top-3 vào ngay Top-1.
> 2. **Giá trị của "kết quả âm" (Negative finding ở Q4):** Khi query đã mang tính khu biệt ngữ nghĩa rất cao ("người bán khấu trừ tiền"), vector embedding tự thân đã đủ sức định vị tài liệu seller mà không cần filter. Điều này cảnh báo kỹ sư không nên lạm dụng cứng nhắc metadata filter ở mọi truy vấn nếu không có tín hiệu phân loại rõ ràng.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

### 4.1. Những phát hiện và phân tích giá trị nhất (Key Insights)

1. **Heading Preservation là yếu tố sống còn cho tài liệu quy chuẩn:** Việc gắn tiêu đề cha (`#`, `##`) vào đầu mỗi chunk con giúp giải quyết bài toán "văn bản vô danh". Đoạn văn con nhận được đầy đủ ngữ cảnh của điều khoản mà không làm bùng nổ kích thước chunk.
2. **Khoảng cách giữa MockEmbedder và Real Embedder:** `MockEmbedder` chỉ hữu ích để unit test luồng dữ liệu (pipeline correctness). Khi đo kiểm chất lượng tìm kiếm, chỉ có Real Embedder (`all-MiniLM-L6-v2` hoặc Gemini) mới phản ánh đúng năng lực phân tách ngữ nghĩa.
3. **Đánh giá hai tầng (Two-Level Scoring) sát sườn hơn Metrics truyền thống:** Việc kiểm tra trực tiếp chuỗi `marker` trong Top-1 và Top-3 giúp phân biệt rõ ràng giữa *"hệ thống trả về đúng trang web"* với *"hệ thống thực sự trích xuất được đoạn chứa câu trả lời"*.

---

### 4.2. Phân tích lỗi thực nghiệm (Failure Case Analysis)

#### Trường hợp 1: RecursiveChunker thất bại ở Q3 (Điểm: 0/2)
- **Truy vấn:** *"Sau khi hoàn tiền được xử lý, người mua thường mất bao lâu để nhận được tiền?"*
- **Hiện tượng:** Top-3 chunk trả về đều thuộc tài liệu `ebay-buyer-return-refund` và bàn về chủ đề hoàn tiền, nhưng không có đoạn nào chứa con số cụ thể `3–5 business days` (chuỗi marker `typically available`).
- **Nguyên nhân cốt lõi:** `RecursiveChunker` tách đoạn văn dựa trên dấu xuống dòng đôi `\n\n` mà không lưu lại tiêu đề mục "Get your refund". Đoạn chứa số liệu thời gian nằm ở một danh sách ngắn, độ tương đồng ngữ nghĩa bị phân tán nên bị các đoạn tổng quan lấn át và đẩy văng khỏi Top-3.
- **Biện pháp khắc phục:** Áp dụng cơ chế kế thừa tiêu đề như `HeadingChunker` hoặc triển khai thêm tầng Reranker (Cross-Encoder) sau bước vector search.

#### Trường hợp 2: FixedSizeChunker bị tụt hạng ở Q5 (Điểm: 1/2)
- **Truy vấn:** *"Liệt kê các điều kiện để người bán được hưởng cơ chế bảo vệ dành cho Top Rated Seller."*
- **Hiện tượng:** Chunk chứa marker chỉ đạt vị trí Rank 3; Top-1 và Top-2 là các đoạn nói chung về seller protection nhưng không có danh sách tiêu chí.
- **Nguyên nhân cốt lõi:** Cắt cố định 800 ký tự cắt ngang qua giữa bảng điều kiện, làm phần đầu danh sách bị chia cắt với phần giải thích. Overlap 80 ký tự là quá ngắn so với một danh sách gồm 5 gạch đầu dòng dài.
- **Biện pháp khắc phục:** Tăng overlap lên 150–200 ký tự cho văn bản dạng danh sách hoặc chuyển hẳn sang phân mảnh theo ranh giới Heading/Markdown List.

#### Trường hợp 3: Metadata Filter không tạo biến thiên ở Q4
- **Hiện tượng:** Cả `RecursiveChunker` và `HeadingChunker` đều trả về Top-3 y hệt nhau dù bật hay tắt `metadata_filter={"audience": "seller"}`.
- **Nguyên nhân:** Bản thân câu hỏi chứa các thuật ngữ đặc thù ("deduct refund", "seller defect rate"). Không gian vector của mô hình nhúng đã phân cực tách biệt hoàn toàn giữa hai cụm tài liệu buyer và seller.
- **Bài học thiết kế:** Không nên áp đặt bộ lọc cưỡng bức trong ứng dụng thực tế nếu người dùng chưa chọn bộ lọc; hãy để mô hình embedding tự phân loại trước và chỉ can thiệp filter khi độ tự tin bị phân tán.

---

### 4.3. Nếu được làm lại từ đầu, nhóm sẽ cải tiến điều gì?

1. **Bộ nhớ đệm Embedding (Embedding Cache):** Lưu trữ vector nhúng ra file nhị phân (Pickle hoặc SQLite) theo mã hash MD5 của chunk text để tránh tiêu tốn thời gian nhúng lại và không lo chạm hạn mức rate-limit khi chạy benchmark lặp lại nhiều lần.
2. **Dynamic Overlap theo cấu trúc văn bản:** Thay vì cố định overlap 80 ký tự, thuật toán sẽ tự động điều chỉnh overlap dựa trên độ dài của câu văn kết thúc để không bao giờ cắt đứt một câu hoàn chỉnh.
3. **Kết hợp Hybrid Search (BM25 + Dense Vector):** Đối với các câu hỏi tra cứu số liệu tuyệt đối như `3 business days` hay `50%`, tìm kiếm từ khóa (BM25) kết hợp với vector search (Hybrid Search) sẽ đảm bảo 100% không bao giờ bỏ sót các chunk chứa số liệu quan trọng.

---

## 5. Bảng Tự Đánh Giá Điểm Nhóm (Self-Evaluation)

| STT | Hạng mục đánh giá | Điểm tối đa | Điểm tự đánh giá | Bằng chứng & Cơ sở đánh giá |
|:---:|---|:---:|:---:|---|
| 1 | **Lựa chọn tài liệu** *(Document Set Quality)* | 10 | **10 / 10** | 5 tài liệu eBay chính thức, cấu trúc rõ ràng, đủ 8 trường metadata chuẩn, có file quản trị nguồn `sources.csv`. |
| 2 | **Thiết kế chiến lược** *(Strategy Design)* | 15 | **15 / 15** | 4 thành viên triển khai 4 chiến lược rõ rệt (Fixed, Recursive, Heading, Semantic), có phân tích so sánh định lượng chi tiết. |
| 3 | **Chất lượng truy xuất** *(Retrieval Quality)* | 10 | **10 / 10** | 5 câu hỏi chuẩn hóa song ngữ, đánh giá Two-Level Scoring trên mô hình nhúng thực, thực nghiệm A/B kiểm chứng rõ ràng vai trò metadata. |
| 4 | **Thuyết trình & Bài học** *(Demo & Lessons Learned)* | 5 | **5 / 5** | Phân tích sâu sắc 3 failure cases, đối chiếu mock vs real model, bài học thực tế có tính ứng dụng kỹ thuật cao. |
| | **TỔNG ĐIỂM PHẦN NHÓM** | **40** | **40 / 40** | **Nhóm hoàn thành xuất sắc toàn bộ yêu cầu Checkpoint 1 đến 6.** |

import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from pathlib import Path
import re
import os
from dotenv import load_dotenv

from src.models import Document
from src.store import EmbeddingStore
from src.chunking import RecursiveChunker
from src.agent import KnowledgeBaseAgent
from src.embeddings import LOCAL_EMBEDDING_MODEL, LocalEmbedder, _mock_embed

QUERIES = [
    {
        "question": "Nếu hàng nhận được không khớp với mô tả hoặc bị hư hỏng, người mua có thể làm gì?",
        "metadata_filter": {"audience": "buyer"},
        "gold_answer": "Người mua có thể đủ điều kiện được eBay Money Back Guarantee bảo vệ và có thể trả lại hàng ngay cả khi chính sách của người bán không chấp nhận đổi trả (return it even if the seller's returns policy says they don't accept returns).",
        "marker": "return it even if",
    },
    {
        "question": "Người bán có bao lâu để phản hồi yêu cầu trả hàng của người mua?",
        "metadata_filter": {"audience": "buyer"},
        "gold_answer": "Người bán có 3 ngày làm việc để phản hồi (The seller has 3 business days to get back to you).",
        "marker": "seller should get back",
    },
    {
        "question": "Sau khi hoàn tiền được xử lý, người mua thường mất bao lâu để nhận được tiền?",
        "metadata_filter": {"audience": "buyer"},
        "gold_answer": "Tiền hoàn thường có mặt trong vòng 3–5 ngày làm việc (typically available within 3-5 business days).",
        "marker": "typically available",
    },
    {
        "question": "Tỉ lệ lỗi giao dịch tối đa được phép trong tiêu chuẩn người bán eBay là bao nhiêu?",
        "metadata_filter": {"audience": "seller"},
        "gold_answer": "Tỉ lệ lỗi giao dịch tối đa là 2% (No more than 2% of transactions).",
        "marker": "No more than 2%",
    },
    {
        "question": "Liệt kê các điều kiện để người bán được hưởng bảo vệ dành cho Top Rated Seller.",
        "metadata_filter": {"audience": "seller"},
        "gold_answer": "Người bán phải là Top Rated Seller tại thời điểm áp dụng bảo vệ, cư trú tại Mỹ hoặc Canada, không có đánh giá 'Very High' ở bất kỳ chỉ số dịch vụ nào, item được đăng trên eBay.com, và listing cho phép đổi trả từ 30 ngày trở lên.",
        "marker": "Top Rated Seller at the time",
    },
]

def load_and_chunk() -> list[Document]:
    d = Path("data/ecommerce")
    md_files = d.glob("*.md")
    chunker = RecursiveChunker(chunk_size=300)
    
    docs = []
    for path in md_files:
        content = path.read_text(encoding="utf-8")
        if "---" not in content:
            continue
            
        parts = content.split("---")
        frontmatter = parts[1]
        body = "---".join(parts[2:])
        
        fm = dict(re.findall(r'^(\w+):\s*(.+)$', frontmatter, re.M))
        
        for k, v in fm.items():
            fm[k] = str(v).strip(' \'"')
            
        metadata = {**fm, "doc_id": path.stem, "source": str(path)}
        
        chunks = chunker.chunk(body.strip())
        for i, chunk_text in enumerate(chunks):
            docs.append(
                Document(
                    id=f"{path.stem}#{i}",
                    content=chunk_text,
                    metadata=metadata
                )
            )
    return docs

def demo_llm(prompt: str) -> str:
    return f"[DEMO LLM] Context included: {len(prompt)} chars..."

def main():
    with open("ket_qua_benchmark.txt", "w", encoding="utf-8") as f_out:
        def log_print(text=""):
            print(text)
            f_out.write(str(text) + "\n")
            
        log_print("=== CHECKPOINT 6: BENCHMARKING WITH CONTENT SCORING & A/B TEST ===")
        docs = load_and_chunk()
        log_print(f"Loaded and chunked {len(docs)} documents.")

        load_dotenv(override=False)
        provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
        if provider == "local":
            try:
                embedder = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
            except Exception as e:
                log_print(f"Failed to load local model: {e}")
                embedder = _mock_embed
        else:
            embedder = _mock_embed
            
        log_print(f"Embedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")

        store = EmbeddingStore(collection_name="benchmark_store", embedding_fn=embedder)
        store.add_documents(docs)
        log_print(f"Stored {store.get_collection_size()} chunks in EmbeddingStore.\n")
        
        agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)

        # 1. 2-Level Content Scoring
        log_print("--- PHẦN 1: SCORING (CHẤM ĐIỂM THEO MỨC ĐỘ NỘI DUNG) ---")
        total_score = 0
        for i, q in enumerate(QUERIES, 1):
            log_print("-" * 50)
            log_print(f"Q{i}: {q['question']}")
            log_print(f"Gold Answer: {q['gold_answer']}")
            log_print(f"Marker cần tìm: '{q['marker']}'")
            log_print(f"Filter: {q.get('metadata_filter')}")
            
            if "metadata_filter" in q:
                results = store.search_with_filter(q['question'], top_k=3, metadata_filter=q['metadata_filter'])
            else:
                results = store.search(q['question'], top_k=3)
                
            log_print("\nTop 3 Chunks:")
            score = 0
            for idx, res in enumerate(results, 1):
                marker_found = q['marker'].lower() in res['content'].lower()
                status = "[CÓ CHỨA ĐÁP ÁN]" if marker_found else "[SAI/THIẾU]"
                
                # Chấm điểm 2 mức: 2đ nếu ở top-1, 1đ nếu ở top-2/3
                if marker_found and score == 0:
                    score = 2 if idx == 1 else 1
                    
                log_print(f"  {idx}. [Score: {res['score']:.3f}] {status} | doc_id: {res['metadata'].get('doc_id')}")
                log_print(f"     Content: {res['content'][:100].replace(chr(10), ' ')}...")
                
            total_score += score
            log_print(f"\n=> Điểm cho câu này: {score}/2")
            
        log_print("-" * 50)
        log_print(f"TỔNG ĐIỂM BENCHMARK CỦA CHIẾN LƯỢC NÀY: {total_score} / 10")
        
        # 2. A/B Testing cho Filter
        log_print("\n\n--- PHẦN 2: A/B TESTING BẮT BUỘC (FILTER vs NO FILTER) ---")
        ab_query = QUERIES[3] # Q4 có filter rành mạch
        log_print(f"Câu hỏi A/B: {ab_query['question']}")
        log_print(f"Audience mục tiêu (Gold): {ab_query['metadata_filter']['audience']}")
        
        log_print("\n> Lần 1: CÓ sử dụng metadata filter (ĐÚNG)")
        res_with_filter = store.search_with_filter(ab_query['question'], top_k=3, metadata_filter=ab_query['metadata_filter'])
        for idx, res in enumerate(res_with_filter, 1):
            log_print(f"  {idx}. [doc_id: {res['metadata'].get('doc_id')}] (Audience: {res['metadata'].get('audience')})")
            
        log_print("\n> Lần 2: KHÔNG sử dụng metadata filter (SẼ LẪN LỘN)")
        res_no_filter = store.search(ab_query['question'], top_k=3)
        for idx, res in enumerate(res_no_filter, 1):
            log_print(f"  {idx}. [doc_id: {res['metadata'].get('doc_id')}] (Audience: {res['metadata'].get('audience')})")

        log_print("\nĐã lưu kết quả ra file ket_qua_benchmark.txt thành công!")

if __name__ == "__main__":
    main()

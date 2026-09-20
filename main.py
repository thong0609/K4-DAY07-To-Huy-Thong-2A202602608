from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent import KnowledgeBaseAgent
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

SAMPLE_FILES = [
    "data/ecommerce/ebay-buyer-money-back-guarantee.md",
    "data/ecommerce/ebay-buyer-return-refund.md",
    "data/ecommerce/ebay-buyer-return-shipping.md",
    "data/ecommerce/ebay-seller-protections.md",
    "data/ecommerce/ebay-seller-standards.md",
]

def parse_markdown_with_frontmatter(content: str) -> tuple[dict, str]:
    metadata = {}
    lines = content.split('\n')
    if lines and lines[0].strip() == '---':
        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_idx = i
                break
        
        if end_idx != -1:
            for i in range(1, end_idx):
                line = lines[i].strip()
                if ':' in line:
                    key, val = line.split(':', 1)
                    val = val.split('#')[0].strip()
                    val = val.strip(' \'"')
                    metadata[key.strip()] = val
            content = '\n'.join(lines[end_idx+1:])
    return metadata, content


def load_documents_from_files(file_paths: list[str]) -> list[Document]:
    """Load documents from file paths for the manual demo."""
    allowed_extensions = {".md", ".txt"}
    documents: list[Document] = []

    for raw_path in file_paths:
        path = Path(raw_path)

        if path.suffix.lower() not in allowed_extensions:
            print(f"Skipping unsupported file type: {path} (allowed: .md, .txt)")
            continue

        if not path.exists() or not path.is_file():
            print(f"Skipping missing file: {path}")
            continue

        content = path.read_text(encoding="utf-8")
        metadata, content = parse_markdown_with_frontmatter(content)
        
        metadata["source"] = str(path)
        metadata["extension"] = path.suffix.lower()

        documents.append(
            Document(
                id=metadata.get("doc_id", path.stem),
                content=content.strip(),
                metadata=metadata,
            )
        )

    return documents


def demo_llm(prompt: str) -> str:
    """A simple mock LLM for manual RAG testing."""
    preview = prompt[:400].replace("\n", " ")
    return f"[DEMO LLM] Generated answer from prompt preview: {preview}..."


def run_manual_demo(question: str | None = None, sample_files: list[str] | None = None) -> int:
    files = sample_files or SAMPLE_FILES
    query = question or "Summarize the key information from the loaded files."

    print("=== Manual File Test ===")
    print("Accepted file types: .md, .txt")
    print("Input file list:")
    for file_path in files:
        print(f"  - {file_path}")

    docs = load_documents_from_files(files)
    if not docs:
        print("\nNo valid input files were loaded.")
        print("Create files matching the sample paths above, then rerun:")
        print("  python3 main.py")
        return 1

    print(f"\nLoaded {len(docs)} documents")
    for doc in docs:
        print(f"  - {doc.id}: {doc.metadata['source']}")

    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            embedder = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "openai":
        try:
            embedder = OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "gemini":
        try:
            embedder = GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    else:
        embedder = _mock_embed

    print(f"\nEmbedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")

    # Chunking step
    from src.chunking import RecursiveChunker
    chunker = RecursiveChunker(chunk_size=300)
    chunked_docs = []
    for doc in docs:
        chunks = chunker.chunk(doc.content)
        for i, c_text in enumerate(chunks):
            chunk_id = f"{doc.id}_chunk_{i}"
            chunked_docs.append(Document(id=chunk_id, content=c_text, metadata=doc.metadata))
            
    print(f"Chunked {len(docs)} documents into {len(chunked_docs)} chunks.")

    store = EmbeddingStore(collection_name="manual_test_store", embedding_fn=embedder)
    store.add_documents(chunked_docs)

    print(f"\nStored {store.get_collection_size()} documents in EmbeddingStore")
    print("\n=== EmbeddingStore Search Test ===")
    print(f"Query: {query}")
    search_results = store.search(query, top_k=3)
    for index, result in enumerate(search_results, start=1):
        print(f"{index}. score={result['score']:.3f} source={result['metadata'].get('source')}")
        print(f"   content preview: {result['content'][:120].replace(chr(10), ' ')}...")

    print("\n=== KnowledgeBaseAgent Test ===")
    agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)
    print(f"Question: {query}")
    print("Agent answer:")
    print(agent.answer(query, top_k=3))
    
    print("\n=== Filter Test (Audience: buyer) ===")
    filter_query = "What is the return policy?"
    print(f"Question: {filter_query}")
    results = store.search_with_filter(filter_query, top_k=3, metadata_filter={"audience": "buyer"})
    for index, result in enumerate(results, start=1):
        print(f"{index}. source={result['metadata'].get('source')} | audience={result['metadata'].get('audience')}")
        print(f"   content preview: {result['content'][:100].replace(chr(10), ' ')}...")
        
    return 0


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else None
    return run_manual_demo(question=question)


if __name__ == "__main__":
    raise SystemExit(main())

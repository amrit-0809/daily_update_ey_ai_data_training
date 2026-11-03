"""Exercise 2 - LlamaIndex retrieval over the Harborlight museum documents.

Usage:
    python 02_llamaindex_museum.py                     # interactive prompt
    python 02_llamaindex_museum.py "your question"     # single question
    python 02_llamaindex_museum.py --test              # run the 6 test questions
"""
import sys
from pathlib import Path

import chromadb
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "Documents"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION = "museum_llamaindex"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 2

TEST_QUESTIONS = [
    "When does the museum close on Thursdays?",
    "What is the adult admission ticket price?",
    "What age group can join Robotics Starter Lab?",
    "When does Space Explorers take place?",
    "What happens if the museum cancels a workshop?",
    "Is free parking available at the museum?",
]


def build_index() -> VectorStoreIndex:
    # Local MiniLM embeddings only - no OpenAI, and no LLM needed for retrieval.
    Settings.embed_model = HuggingFaceEmbedding(model_name=MODEL_NAME)

    documents = SimpleDirectoryReader(str(DOCS_DIR), required_exts=[".txt"]).load_data()

    splitter = SentenceSplitter(chunk_size=150, chunk_overlap=20)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"Loaded {len(documents)} documents -> {len(nodes)} nodes")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # Start fresh each run so re-running does not duplicate nodes.
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.get_or_create_collection(COLLECTION)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex(nodes, storage_context=storage_context)
    print(f"Stored nodes in ChromaDB collection '{COLLECTION}'")
    return index


def search(retriever, question: str) -> None:
    print("\n" + "=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)
    results = retriever.retrieve(question)
    for rank, result in enumerate(results, start=1):
        source = result.node.metadata.get("file_name", "unknown")
        # LlamaIndex reports a similarity score: higher = more similar.
        print(f"\n[{rank}] source: {source} | similarity: {result.score:.4f}")
        print("-" * 80)
        print(result.node.get_content())


def main() -> None:
    index = build_index()
    retriever = index.as_retriever(similarity_top_k=TOP_K)

    args = sys.argv[1:]
    if args == ["--test"]:
        for q in TEST_QUESTIONS:
            search(retriever, q)
    elif args:
        search(retriever, " ".join(args))
    else:
        while True:
            q = input("\nAsk a question (blank to quit): ").strip()
            if not q:
                break
            search(retriever, q)


if __name__ == "__main__":
    main()

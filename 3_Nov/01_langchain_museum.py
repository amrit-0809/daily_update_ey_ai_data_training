"""Exercise 1 - LangChain retrieval over the Harborlight museum documents.

Usage:
    python 01_langchain_museum.py                      # interactive prompt
    python 01_langchain_museum.py "your question"      # single question
    python 01_langchain_museum.py --test               # run the 6 test questions
"""
import sys
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "Documents"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION = "museum_langchain"
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


def load_documents() -> list[Document]:
    """Read every .txt file in Documents/ into a LangChain Document."""
    docs = []
    for path in sorted(DOCS_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        docs.append(Document(page_content=text, metadata={"source": path.name}))
    return docs


def split_documents(docs: list[Document]) -> list[Document]:
    """Split into ~150-token chunks with 20-token overlap (MiniLM tokenizer)."""
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer, chunk_size=150, chunk_overlap=20
    )
    return splitter.split_documents(docs)


def build_vector_store(chunks: list[Document]) -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # Start fresh each run so re-running does not duplicate chunks.
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    store = Chroma(
        client=client,
        collection_name=COLLECTION,
        embedding_function=embeddings,
    )
    store.add_documents(chunks, ids=[f"chunk-{i}" for i in range(len(chunks))])
    return store


def search(store: Chroma, question: str) -> None:
    print("\n" + "=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)
    # Chroma returns a distance: lower = more similar.
    results = store.similarity_search_with_score(question, k=TOP_K)
    for rank, (doc, distance) in enumerate(results, start=1):
        print(f"\n[{rank}] source: {doc.metadata['source']} | distance: {distance:.4f}")
        print("-" * 80)
        print(doc.page_content)


def main() -> None:
    docs = load_documents()
    chunks = split_documents(docs)
    print(f"Loaded {len(docs)} documents -> {len(chunks)} chunks")
    store = build_vector_store(chunks)
    print(f"Stored chunks in ChromaDB collection '{COLLECTION}'")

    args = sys.argv[1:]
    if args == ["--test"]:
        for q in TEST_QUESTIONS:
            search(store, q)
    elif args:
        search(store, " ".join(args))
    else:
        while True:
            q = input("\nAsk a question (blank to quit): ").strip()
            if not q:
                break
            search(store, q)


if __name__ == "__main__":
    main()

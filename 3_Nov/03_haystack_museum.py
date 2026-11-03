"""Exercise 3 - Haystack retrieval over the Harborlight museum documents.

Usage:
    python 03_haystack_museum.py                       # interactive prompt
    python 03_haystack_museum.py "your question"       # single question
    python 03_haystack_museum.py --test                # run the 6 test questions
"""
import sys
from pathlib import Path

from haystack import Document, Pipeline
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.writers import DocumentWriter
from haystack.document_stores.in_memory import InMemoryDocumentStore

# Haystack 3.x ships the Sentence-Transformers embedders as a separate integration
# (pip install sentence-transformers-haystack); Haystack 2.x had them built in.
try:
    from haystack_integrations.components.embedders.sentence_transformers import (
        SentenceTransformersDocumentEmbedder,
        SentenceTransformersTextEmbedder,
    )
except ImportError:  # Haystack 2.x
    from haystack.components.embedders import (
        SentenceTransformersDocumentEmbedder,
        SentenceTransformersTextEmbedder,
    )

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "Documents"
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
    return [
        Document(content=p.read_text(encoding="utf-8"), meta={"source": p.name})
        for p in sorted(DOCS_DIR.glob("*.txt"))
    ]


def build_indexing_pipeline(store: InMemoryDocumentStore) -> Pipeline:
    """DocumentSplitter -> DocumentEmbedder -> DocumentWriter."""
    pipe = Pipeline()
    pipe.add_component(
        "splitter", DocumentSplitter(split_by="word", split_length=100, split_overlap=15)
    )
    pipe.add_component("embedder", SentenceTransformersDocumentEmbedder(model=MODEL_NAME))
    pipe.add_component("writer", DocumentWriter(document_store=store))
    pipe.connect("splitter.documents", "embedder.documents")
    pipe.connect("embedder.documents", "writer.documents")
    return pipe


def build_query_pipeline(store: InMemoryDocumentStore) -> Pipeline:
    """TextEmbedder -> InMemoryEmbeddingRetriever."""
    pipe = Pipeline()
    pipe.add_component("text_embedder", SentenceTransformersTextEmbedder(model=MODEL_NAME))
    pipe.add_component(
        "retriever", InMemoryEmbeddingRetriever(document_store=store, top_k=TOP_K)
    )
    pipe.connect("text_embedder.embedding", "retriever.query_embedding")
    return pipe


def search(query_pipe: Pipeline, question: str) -> None:
    print("\n" + "=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)
    result = query_pipe.run({"text_embedder": {"text": question}})
    for rank, doc in enumerate(result["retriever"]["documents"], start=1):
        # Haystack reports a similarity score: higher = more similar.
        print(f"\n[{rank}] source: {doc.meta['source']} | similarity: {doc.score:.4f}")
        print("-" * 80)
        print(doc.content.strip())


def main() -> None:
    store = InMemoryDocumentStore()
    docs = load_documents()
    build_indexing_pipeline(store).run({"splitter": {"documents": docs}})
    print(f"Loaded {len(docs)} documents -> {store.count_documents()} chunks in InMemoryDocumentStore")

    query_pipe = build_query_pipeline(store)

    args = sys.argv[1:]
    if args == ["--test"]:
        for q in TEST_QUESTIONS:
            search(query_pipe, q)
    elif args:
        search(query_pipe, " ".join(args))
    else:
        while True:
            q = input("\nAsk a question (blank to quit): ").strip()
            if not q:
                break
            search(query_pipe, q)


if __name__ == "__main__":
    main()

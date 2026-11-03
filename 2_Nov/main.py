
import os
from pathlib import Path

import chromadb
import tiktoken

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from openai import OpenAI

from guardrails import (
    check_input,
    check_output,
    check_relevance,
    REFUSAL_MESSAGE
)


# =====================================================
# 1. CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent

DOCUMENTS_DIR = BASE_DIR / "Documents"
CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "company_documents"

CHUNK_SIZE = 120
CHUNK_OVERLAP = 20

TOP_K = 2

# Load environment variables
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
)

if not API_KEY:
    raise ValueError(
        "OpenRouter API key missing. "
        "Add OPENROUTER_API_KEY to your .env file."
    )


# =====================================================
# 2. INITIALIZE OPENROUTER CLIENT
# =====================================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "Simple Python RAG"
    }
)


# =====================================================
# 3. LOAD LOCAL EMBEDDING MODEL
# =====================================================

print("\nLoading embedding model...")

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Embedding model loaded successfully!")

print(
    "Embedding dimensions:",
    embedding_model.get_sentence_embedding_dimension()
)


# =====================================================
# 4. INITIALIZE TOKENIZER
# =====================================================

tokenizer = tiktoken.get_encoding("cl100k_base")


# =====================================================
# 5. READ DOCUMENTS
# =====================================================

def read_documents():

    documents = {}

    print("\n========== DOCUMENT READING ==========")

    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError(
            f"Documents folder not found: {DOCUMENTS_DIR}"
        )

    files = sorted(DOCUMENTS_DIR.glob("*.txt"))

    if not files:
        raise ValueError(
            "No .txt files found inside Documents folder."
        )

    for file_path in files:

        text = file_path.read_text(
            encoding="utf-8"
        )

        documents[file_path.name] = text

        tokens = tokenizer.encode(text)

        print("\nFilename:", file_path.name)

        print("\nDocument content:")
        print(text)

        print("\nToken count:", len(tokens))

        print("-" * 60)

    return documents


# =====================================================
# 6. CHUNK DOCUMENTS
# =====================================================

def create_chunks(documents):

    all_chunks = []

    all_metadata = []

    print("\n========== DOCUMENT CHUNKING ==========")

    step = CHUNK_SIZE - CHUNK_OVERLAP

    for filename, text in documents.items():

        tokens = tokenizer.encode(text)

        file_chunks = []

        for start in range(0, len(tokens), step):

            end = start + CHUNK_SIZE

            chunk_tokens = tokens[start:end]

            if not chunk_tokens:
                continue

            chunk_text = tokenizer.decode(
                chunk_tokens
            )

            if not chunk_text.strip():
                continue

            file_chunks.append(chunk_text)

            all_chunks.append(chunk_text)

            all_metadata.append({
                "source": filename,
                "chunk_index": len(file_chunks) - 1
            })

        print(
            f"\nFile: {filename}"
        )

        print(
            "Number of chunks:",
            len(file_chunks)
        )

        if file_chunks:
            print("\nSample chunk:")
            print(file_chunks[0])

    print("\nTotal chunks:", len(all_chunks))

    return all_chunks, all_metadata


# =====================================================
# 7. GENERATE EMBEDDINGS
# =====================================================

def generate_embeddings(chunks):

    print("\n========== EMBEDDING GENERATION ==========")

    embeddings = embedding_model.encode(
        chunks,
        convert_to_numpy=True,
        show_progress_bar=True
    )

    print(
        "Total embeddings:",
        len(embeddings)
    )

    print(
        "Vector dimensions:",
        embeddings.shape[1]
    )

    return embeddings


# =====================================================
# 8. CREATE PERSISTENT CHROMADB
# =====================================================

def create_vector_database(
    chunks,
    metadata,
    embeddings
):

    print("\n========== CHROMADB STORAGE ==========")

    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    # Rebuild this exercise's collection on each run
    try:
        chroma_client.delete_collection(
            name=COLLECTION_NAME
        )
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine"
        }
    )

    ids = [
        f"chunk_{i}"
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadata
    )

    print("Documents stored successfully!")

    print(
        "Total records:",
        collection.count()
    )

    print(
        "Database location:",
        CHROMA_DIR
    )

    return collection


# =====================================================
# 9. SEARCH DOCUMENTS IN CHROMADB
# =====================================================

def search_documents(collection, question):

    print("\n========== CHROMADB SEARCH ==========")

    question_embedding = embedding_model.encode(
        [question]
    ).tolist()

    total_records = collection.count()

    if total_records == 0:
        print("No documents available.")
        return []

    results = collection.query(
        query_embeddings=question_embedding,
        n_results=min(TOP_K, total_records),
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    retrieved_chunks = []

    for i, chunk in enumerate(
        results["documents"][0]
    ):

        source = results["metadatas"][0][i]["source"]

        chunk_index = results["metadatas"][0][i]["chunk_index"]

        distance = results["distances"][0][i]

        print(f"\nResult {i + 1}")

        print("Source:", source)

        print("Chunk index:", chunk_index)

        print(
            "Cosine distance:",
            round(distance, 4)
        )

        print("\nRetrieved text:")
        print(chunk)

        retrieved_chunks.append({
            "text": chunk,
            "source": source,
            "distance": distance
        })

    return retrieved_chunks


# =====================================================
# 10. GENERATE AI ANSWER USING OPENROUTER
# =====================================================

def generate_answer(question, retrieved_chunks):

    print("\n========== OPENROUTER AI ==========")

    if not retrieved_chunks:
        return (
            "I cannot find the answer "
            "in the provided documents."
        )

    context_parts = []

    for item in retrieved_chunks:

        context_parts.append(
            f"Source: {item['source']}\n"
            f"Content: {item['text']}"
        )

    context = "\n\n".join(context_parts)

    system_prompt = """
You are a company policy question-answering assistant.

Your task is to answer questions using ONLY the
provided document context.

Rules:

1. Use only the supplied context.
2. Do not use outside knowledge.
3. Do not invent or assume information.
4. If the answer is missing, say:
   "I cannot find the answer in the provided documents."
5. Give a clear and concise answer.
6. Preserve exact numbers, dates and time periods
   from the documents.
"""

    user_prompt = f"""
DOCUMENT CONTEXT:

{context}


USER QUESTION:

{question}


Provide the answer based only on the document context.
"""

    try:

        response = client.chat.completions.create(

            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],

            temperature=0

        )

        answer = response.choices[0].message.content

        return answer or (
            "The AI model returned an empty response."
        )

    except Exception as e:

        print("\nOpenRouter API error:", str(e))

        return "Unable to generate an AI answer. Check the API key, model availability and connection."


# =====================================================
# 11. ASK A QUESTION
# =====================================================

def ask_question(collection, question):

    print("\n" + "=" * 65)

    print("QUESTION:", question)

    print("=" * 65)

    # Guardrail 1: input checks (PII, injection, sensitive, harmful)
    input_check = check_input(question)

    if not input_check.allowed:

        message = (
            "Your question was blocked by a safety guardrail: "
            + input_check.reason
        )

        print(f"\n[GUARDRAIL BLOCKED - {input_check.layer}]")

        print("\n========== FINAL AI ANSWER ==========")

        print(message)

        print("=" * 65)

        return message

    retrieved_chunks = search_documents(
        collection,
        question
    )

    # Guardrail 2: relevance (refuse off-topic questions without calling the AI)
    if retrieved_chunks:

        relevance_check = check_relevance(
            retrieved_chunks[0]["distance"]
        )

        print(f"\n[GUARDRAIL] {relevance_check.reason}")

        if not relevance_check.allowed:

            print("\n========== FINAL AI ANSWER ==========")

            print(REFUSAL_MESSAGE)

            print("=" * 65)

            return REFUSAL_MESSAGE

    answer = generate_answer(
        question,
        retrieved_chunks
    )

    # Guardrail 3: output checks (PII redaction, prompt leak, number grounding)
    context = "\n".join(
        item["text"] for item in retrieved_chunks
    )

    answer, warnings = check_output(
        answer,
        context
    )

    for warning in warnings:
        print(f"\n[GUARDRAIL WARNING] {warning}")

    print("\n========== FINAL AI ANSWER ==========")

    print(answer)

    print("=" * 65)

    return answer


# =====================================================
# 12. MAIN APPLICATION
# =====================================================

def main():

    print("\n")
    print("*" * 65)

    print("       SIMPLE PYTHON RAG APPLICATION")

    print("       ChromaDB + Local Embeddings")

    print("       OpenRouter AI")

    print("*" * 65)

    # Read documents
    documents = read_documents()

    # Create chunks
    chunks, metadata = create_chunks(
        documents
    )

    if not chunks:
        raise ValueError(
            "No chunks generated from documents."
        )

    # Generate embeddings
    embeddings = generate_embeddings(
        chunks
    )

    # Store in ChromaDB
    collection = create_vector_database(
        chunks,
        metadata,
        embeddings
    )

    print("\n========== APPLICATION READY ==========")

    print("You can now ask questions about your documents.")

    print("\nAvailable test questions:")

    test_questions = [
        "How many annual leave days do employees receive?",
        "Which days must employees work from the office?",
        "How quickly should a lost company laptop be reported?",
        "How quickly are Priority 1 incidents acknowledged?",
        "What is the company travel allowance per day?"
    ]

    for i, question in enumerate(
        test_questions,
        start=1
    ):
        print(f"{i}. {question}")

    print("\nType 'test' to run all five questions.")

    print("Type 'exit' to close the application.")

    # Interactive question loop
    while True:

        question = input(
            "\nEnter your question: "
        ).strip()

        if question.lower() == "exit":

            print("\nApplication closed.")

            break

        elif question.lower() == "test":

            for test_question in test_questions:

                ask_question(
                    collection,
                    test_question
                )

        elif question:

            ask_question(
                collection,
                question
            )

        else:

            print("Please enter a valid question.")



"""Lesson 8: evaluate whether correct evidence appears in top 3 chunks."""
import csv
from time import perf_counter
from rag_core import PROJECT_DIR, search_chunks

TESTS = [
    ("How many annual leave days do full-time employees receive?", "18 days of paid annual leave"),
    ("Which days are mandatory office days?", "Tuesdays and Thursdays"),
    ("How many paid sick leave days are provided?", "eight days of paid sick leave"),
    ("When must a lost laptop be reported?", "within 24 hours"),
    ("What is the response target for a Priority 1 incident?", "within 30 minutes"),
]

rows = []
for question, expected_text in TESTS:
    start = perf_counter()
    matches = search_chunks(question, top_k=3)
    seconds = perf_counter() - start

    retrieved_text = " ".join(m["text"] for m in matches)
    found = expected_text.lower() in retrieved_text.lower()
    rows.append({
        "question": question,
        "expected_evidence": expected_text,
        "evidence_found": found,
        "top_chunk": matches[0]["id"],
        "top_distance": round(matches[0]["distance"], 4),
        "time_seconds": round(seconds, 2),
    })
    print(f"{'PASS' if found else 'FAIL'} | {question}")
    print(f"  First match: {matches[0]['id']} | distance: {matches[0]['distance']:.4f} | time: {seconds:.2f}s")

score = sum(row["evidence_found"] for row in rows)
print(f"\nRetrieval evidence found: {score}/{len(TESTS)} ({score / len(TESTS):.0%})")

csv_path = PROJECT_DIR / "benchmark_results.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print("Saved:", csv_path)
print("Note: this checks whether evidence is retrieved, not whether the AI answer is correct.")

# =====================================================
# 13. EXECUTION STARTING POINT
# =====================================================

if __name__ == "__main__":

    main()

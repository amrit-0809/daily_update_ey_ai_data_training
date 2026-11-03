
import os
import csv

from datetime import datetime
from time import perf_counter
from statistics import mean, median

from dotenv import load_dotenv
from openai import OpenAI

from rag_core import PROJECT_DIR, search_chunks


# ==========================================
# 1. CONFIGURATION
# ==========================================

load_dotenv(PROJECT_DIR / ".env")

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise SystemExit("OPENROUTER_API_KEY missing in .env")


# ==========================================
# 2. OPENROUTER CLIENT
# ==========================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "RAG Speed Benchmark"
    },
    timeout=120.0,
    max_retries=0
)


# ==========================================
# 3. CHAT MODELS
# ==========================================

MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "xingchen-agi/xing4.0-29b-a4b:free",
    "google/gemma-4-31b-it:free",
]

# Number of tests per model
TEST_RUNS = 3

# Same generation settings for every model
MAX_TOKENS = 500
TEMPERATURE = 0


# ==========================================
# 4. CSV CONFIGURATION
# ==========================================

CSV_PATH = PROJECT_DIR / "model_speed_results.csv"

CSV_FIELDS = [
    "timestamp",
    "question",
    "model",
    "actual_model",
    "run",
    "response_time_seconds",
    "status",
    "error"
]


# ==========================================
# 5. SAVE CSV
# ==========================================

def save_result(row):

    file_exists = CSV_PATH.exists()

    with CSV_PATH.open(
        "a",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


# ==========================================
# 6. GENERATE ANSWER AND MEASURE SPEED
# ==========================================

def test_model(model_name, question, context):

    prompt = f"""
You are a company policy assistant.

Answer using ONLY the reference documents.

Do not use outside knowledge.
Do not invent information.
Keep the answer concise.

REFERENCE DOCUMENTS:

{context}

QUESTION:

{question}

ANSWER:
"""

    start = perf_counter()

    response = client.chat.completions.create(

        model=model_name,

        messages=[
            {
                "role": "system",
                "content": (
                    "Answer accurately using only "
                    "the supplied document context."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS

    )

    elapsed = perf_counter() - start

    answer = response.choices[0].message.content

    actual_model = response.model or model_name

    if not answer:
        raise ValueError("Empty response received")

    return elapsed, actual_model


# ==========================================
# 7. COMPARE MODEL SPEED
# ==========================================

def compare_models(question):

    print("\n" + "=" * 70)
    print("RETRIEVING DOCUMENT CONTEXT")
    print("=" * 70)

    # Retrieve only once
    retrieval_start = perf_counter()

    matches = search_chunks(
        question,
        top_k=3
    )

    retrieval_time = perf_counter() - retrieval_start

    if not matches:
        print("No relevant document chunks found.")
        return

    # Identical context for every model
    context = "\n\n".join(
        f"[SOURCE {m['id']}]\n{m['text']}"
        for m in matches
    )

    print("Retrieved chunks:", len(matches))
    print(f"Retrieval time: {retrieval_time:.3f}s")

    print("\n" + "=" * 70)
    print("STARTING MODEL SPEED BENCHMARK")
    print("=" * 70)

    results = []

    # ======================================
    # TEST EACH MODEL
    # ======================================

    for model_name in MODELS:

        print("\n" + "-" * 70)
        print("MODEL:", model_name)
        print("-" * 70)

        model_times = []

        for run in range(1, TEST_RUNS + 1):

            print(f"\nRun {run}/{TEST_RUNS}")

            try:

                elapsed, actual_model = test_model(
                    model_name,
                    question,
                    context
                )

                model_times.append(elapsed)

                print(f"Response time: {elapsed:.3f} seconds")

                row = {
                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    "question": question,
                    "model": model_name,
                    "actual_model": actual_model,
                    "run": run,
                    "response_time_seconds": round(elapsed, 3),
                    "status": "Success",
                    "error": ""
                }

            except Exception as error:

                print("FAILED:", str(error))

                row = {
                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    "question": question,
                    "model": model_name,
                    "actual_model": "",
                    "run": run,
                    "response_time_seconds": "",
                    "status": "Failed",
                    "error": str(error)
                }

            save_result(row)
            results.append(row)

        # Model statistics
        if model_times:

            print("\nMODEL STATISTICS")

            print(
                f"Average: {mean(model_times):.3f} seconds"
            )

            print(
                f"Median: {median(model_times):.3f} seconds"
            )

            print(
                f"Fastest run: {min(model_times):.3f} seconds"
            )

    # ======================================
    # 8. FINAL COMPARISON
    # ======================================

    print("\n")
    print("=" * 85)
    print("MODEL SPEED COMPARISON")
    print("=" * 85)

    print(
        f"{'MODEL':45} "
        f"{'AVG TIME':12} "
        f"{'MEDIAN':12} "
        f"{'RUNS':8}"
    )

    print("-" * 85)

    summary = []

    for model_name in MODELS:

        successful_times = [
            float(r["response_time_seconds"])
            for r in results
            if r["model"] == model_name
            and r["status"] == "Success"
        ]

        if successful_times:

            avg_time = mean(successful_times)
            median_time = median(successful_times)

            summary.append({
                "model": model_name,
                "average": avg_time,
                "median": median_time,
                "runs": len(successful_times)
            })

            print(
                f"{model_name:45} "
                f"{avg_time:>8.3f}s "
                f"{median_time:>8.3f}s "
                f"{len(successful_times):>5}"
            )

        else:

            print(f"{model_name:45} FAILED")

    # ======================================
    # 9. FASTEST MODEL
    # ======================================

    print("\n" + "=" * 85)

    if summary:

        fastest = min(
            summary,
            key=lambda x: x["average"]
        )

        print("FASTEST MODEL:")

        print(fastest["model"])

        print(
            f"Average response time: "
            f"{fastest['average']:.3f} seconds"
        )

        print(
            f"Successful runs: "
            f"{fastest['runs']}/{TEST_RUNS}"
        )

    else:

        print("No model completed successfully.")

    print("\nRetrieval time:", round(retrieval_time, 3), "seconds")

    print("\nCSV FILE:")
    print(CSV_PATH)

    print("=" * 85)


# ==========================================
# 10. MAIN
# ==========================================

def main():

    print("\n")
    print("*" * 70)
    print("         RAG MODEL SPEED BENCHMARK")
    print("         OPENROUTER FREE MODELS")
    print("*" * 70)

    print("\nModels:")

    for i, model in enumerate(MODELS, 1):
        print(f"{i}. {model}")

    print("\nRuns per model:", TEST_RUNS)

    while True:

        question = input(
            "\nEnter your question (or exit): "
        ).strip()

        if question.lower() in {"exit", "quit"}:
            print("Benchmark completed.")
            break

        if not question:
            print("Please enter a question.")
            continue

        compare_models(question)


if __name__ == "__main__":
    main()

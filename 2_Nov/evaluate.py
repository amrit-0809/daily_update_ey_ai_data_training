
"""
Lesson 8:
Evaluate whether correct evidence appears
in the top 3 retrieved chunks.
"""

import csv
from time import perf_counter

from rag_core import PROJECT_DIR, search_chunks


# =========================================
# 1. TEST QUESTIONS AND EXPECTED EVIDENCE
# =========================================

TESTS = [

    (
        "How many annual leave days do full-time employees receive?",
        "18 days of paid annual leave"
    ),

    (
        "Which days are mandatory office days?",
        "Tuesdays and Thursdays"
    ),

    (
        "How many paid sick leave days are provided?",
        "eight days of paid sick leave"
    ),

    (
        "When must a lost laptop be reported?",
        "within 24 hours"
    ),

    (
        "What is the response target for a Priority 1 incident?",
        "within 30 minutes"
    ),

]


# =========================================
# 2. RUN RETRIEVAL EVALUATION
# =========================================

rows = []

print("\n======================================")
print("       RAG RETRIEVAL EVALUATION")
print("======================================")

for question, expected_text in TESTS:

    start = perf_counter()

    matches = search_chunks(
        question,
        top_k=3
    )

    seconds = perf_counter() - start

    # Combine retrieved chunk text
    retrieved_text = " ".join(
        match["text"] for match in matches
    )

    # Check expected evidence
    found = (
        expected_text.lower()
        in retrieved_text.lower()
    )

    # Handle empty search results
    if matches:

        top_chunk = matches[0]["id"]

        top_distance = round(
            matches[0]["distance"],
            4
        )

    else:

        top_chunk = "No results"

        top_distance = ""

    # Save results
    rows.append({

        "question": question,

        "expected_evidence": expected_text,

        "evidence_found": found,

        "top_chunk": top_chunk,

        "top_distance": top_distance,

        "time_seconds": round(seconds, 2),

    })

    # Print result
    status = "PASS" if found else "FAIL"

    print(f"\n{status} | {question}")

    print(
        f"  First match: {top_chunk}"
        f" | distance: {top_distance}"
        f" | time: {seconds:.2f}s"
    )


# =========================================
# 3. CALCULATE RETRIEVAL ACCURACY
# =========================================

score = sum(
    row["evidence_found"]
    for row in rows
)

total = len(TESTS)

accuracy = score / total if total else 0

print("\n======================================")

print(
    f"Retrieval evidence found: "
    f"{score}/{total} ({accuracy:.0%})"
)

print("======================================")


# =========================================
# 4. EXPORT RESULTS TO CSV
# =========================================

csv_path = PROJECT_DIR / "benchmark_results.csv"

with csv_path.open(
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=rows[0].keys()
    )

    writer.writeheader()

    writer.writerows(rows)


print("\nBenchmark results saved:")
print(csv_path)

print(
    "\nNote: This evaluates retrieval evidence, "
    "not whether the AI-generated answer is correct."
)

"""Local Python tools used by the AI agent. No framework or external database."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_PATH = ROOT / "knowledge_base.json"
TICKETS_PATH = ROOT / "tickets.json"

STOP_WORDS = {
    "the", "a", "an", "i", "my", "me", "is", "are", "it", "from",
    "to", "and", "or", "on", "in", "at", "with", "for", "when",
    "can", "you", "help", "please", "not", "working", "how", "do",
    "get", "this", "have", "am", "be", "of", "does", "still",
}


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP_WORDS


def search_knowledge_base(query: str) -> dict:
    """Return the best matching support articles using simple keyword overlap."""
    articles = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    query_terms = words(query)
    ranked = []

    for article in articles:
        title_terms = words(article["title"])
        tag_terms = words(" ".join(article["tags"]))
        body_terms = words(article["problem"] + " " + " ".join(article["steps"]))

        score = (
            3 * len(query_terms & title_terms)
            + 2 * len(query_terms & tag_terms)
            + len(query_terms & body_terms)
        )
        if score > 0:
            ranked.append((score, article))

    ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    results = []
    for score, article in ranked[:2]:
        results.append({
            "id": article["id"],
            "title": article["title"],
            "category": article["category"],
            "problem": article["problem"],
            "steps": article["steps"],
            "keyword_score": score,
        })

    return {
        "query": query,
        "results": results,
        "message": (
            "These are the top keyword matches. Explain only supported steps."
            if results else "No matching article found. Do not invent troubleshooting steps."
        ),
    }


def create_support_ticket(
    summary: str,
    category: str,
    priority: str,
    confirm: Callable[[str], str] = input,
) -> dict:
    """Create a ticket in tickets.json, but only after explicit local confirmation."""
    allowed_categories = {"Network", "Software", "Hardware", "Account", "Other"}
    allowed_priorities = {"Low", "Medium", "High"}
    summary = summary.strip()[:300]

    if not summary:
        return {"created": False, "reason": "Ticket summary is missing."}
    if category not in allowed_categories:
        return {"created": False, "reason": "Invalid category."}
    if priority not in allowed_priorities:
        return {"created": False, "reason": "Invalid priority."}

    print("\n--- TICKET APPROVAL REQUIRED ---")
    print("Summary :", summary)
    print("Category:", category)
    print("Priority:", priority)
    approval = confirm("Create this ticket? (y/n): ").strip().lower()
    if approval not in {"y", "yes"}:
        print("Ticket was not created.")
        return {"created": False, "reason": "User declined approval."}

    tickets = json.loads(TICKETS_PATH.read_text(encoding="utf-8"))
    next_id = max(
        [int(ticket["id"].split("-")[-1]) for ticket in tickets] or [0]
    ) + 1
    ticket = {
        "id": f"IT-{next_id:04d}",
        "summary": summary,
        "category": category,
        "priority": priority,
        "status": "Open",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    tickets.append(ticket)
    TICKETS_PATH.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
    return {"created": True, "ticket": ticket}

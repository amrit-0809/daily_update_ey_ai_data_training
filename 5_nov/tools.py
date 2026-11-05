"""Python tools that the AI Library Assistant can call."""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
BOOKS_FILE = BASE_DIR / "books.json"
RESERVATIONS_FILE = BASE_DIR / "reservations.json"

STOP_WORDS = {"the", "and", "for", "with", "book", "books", "about", "related", "a", "an", "of", "to", "on"}


def _load_json(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else []


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Tool 1: search_books
# ---------------------------------------------------------------------------
def search_books(query: str) -> dict:
    """Search books by title, author, or category keyword."""
    books = _load_json(BOOKS_FILE)
    query_lower = query.lower().strip()
    words = [w for w in query_lower.split() if w not in STOP_WORDS and len(w) > 1]

    scored = []
    for book in books:
        text = f"{book['title']} {book['author']} {book['category']}".lower()
        if query_lower and query_lower in text:
            score = 100  # exact phrase match ranks first
        else:
            score = sum(1 for w in words if w in text)
        if score > 0:
            scored.append((score, book))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = [
        {
            **book,
            "status": "Available" if book["available_copies"] > 0 else "Not available",
        }
        for _, book in scored
    ]

    return {"query": query, "match_count": len(results), "books": results}


# ---------------------------------------------------------------------------
# Tool 2: reserve_book
# ---------------------------------------------------------------------------
def load_books() -> list:
    return _load_json(BOOKS_FILE)


def load_reservations() -> list:
    return _load_json(RESERVATIONS_FILE)


def check_reservable(book_id) -> tuple:
    """Return (book, None) if the book can be reserved, else (book_or_None, error_message)."""
    try:
        book_id = int(book_id)
    except (TypeError, ValueError):
        return None, f"Invalid book ID: {book_id}."
    book = next((b for b in load_books() if b["id"] == book_id), None)
    if book is None:
        return None, f"No book found with ID {book_id}."
    if book["available_copies"] <= 0:
        return book, f"'{book['title']}' has no available copies. Reservation not created."
    return book, None


def terminal_confirm(book: dict, customer_name: str) -> bool:
    """Default confirmation: ask in the terminal."""
    print(f"\n  Confirm reservation of '{book['title']}' (ID {book['id']}) for {customer_name}?")
    return input("  Type 'yes' to confirm: ").strip().lower() in ("yes", "y")


def reserve_book(book_id: int, customer_name: str, confirm=terminal_confirm) -> dict:
    """Reserve a book for a customer after the user confirms.

    `confirm(book, customer_name) -> bool` asks the user for approval
    (terminal prompt by default; the web UI passes its own button result).
    """
    book, error = check_reservable(book_id)
    if error:
        return {"success": False, "message": error}

    # Human-in-the-loop confirmation before changing any data
    if not confirm(book, customer_name):
        return {"success": False, "message": "Reservation cancelled by the user. Nothing was saved."}

    books = load_books()
    book = next(b for b in books if b["id"] == book["id"])

    reservations = _load_json(RESERVATIONS_FILE)
    reservation = {
        "reservation_id": len(reservations) + 1,
        "book_id": book["id"],
        "title": book["title"],
        "customer_name": customer_name,
        "reserved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    reservations.append(reservation)
    _save_json(RESERVATIONS_FILE, reservations)

    book["available_copies"] -= 1
    _save_json(BOOKS_FILE, books)

    return {
        "success": True,
        "message": "Reservation created.",
        "reservation": reservation,
        "remaining_copies": book["available_copies"],
    }


# ---------------------------------------------------------------------------
# Tool definitions given to the AI model (OpenAI function-calling format)
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": (
                "Search the library catalogue by book title, author, or topic keyword. "
                "Returns matching books with their ID, author, category and number of available copies. "
                "Use this to answer questions about which books exist or whether a book is available, "
                "and to find a book's ID before reserving it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A title, author name, or keyword such as 'Python' or 'artificial intelligence'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserve_book",
            "description": (
                "Reserve one copy of a book for a customer, using the book's numeric ID. "
                "The user is asked to confirm in the terminal before anything is saved. "
                "If you only know the title, call search_books first to get the ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": "integer", "description": "The numeric book ID, e.g. 101."},
                    "customer_name": {"type": "string", "description": "Name of the customer reserving the book."},
                },
                "required": ["book_id", "customer_name"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "search_books": search_books,
    "reserve_book": reserve_book,
}

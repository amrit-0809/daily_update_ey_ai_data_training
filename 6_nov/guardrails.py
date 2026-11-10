"""
guardrails.py: STEP 2

Guardrails are plain Python checks that run around the LLM:

    user input --> [INPUT guardrails] --> agent --> [OUTPUT guardrail] --> screen
                                            |
                                     [TOOL guardrail]  (inside the tool itself)

Why plain Python instead of asking the LLM to behave?
Because code is deterministic. A system prompt is a request; a guardrail is a rule.
This file has NO LangChain imports, so you can test it on its own:  python guardrails.py
"""
import re

# ---------------------------------------------------------------------------
# Settings: keep "magic numbers" in one place so they're easy to change
# ---------------------------------------------------------------------------
MAX_INPUT_LENGTH = 500
MIN_GUESTS = 1
MAX_GUESTS = 20


# ---------------------------------------------------------------------------
# 1. INPUT VALIDATION: reject empty or excessively long questions
#    Returns an error message (str) or None if the input is fine.
# ---------------------------------------------------------------------------
def validate_input(text: str) -> str | None:
    if not text or not text.strip():
        return "Please type a question. Empty messages can't be processed."
    if len(text) > MAX_INPUT_LENGTH:
        return (f"Your message is {len(text)} characters long. "
                f"Please keep it under {MAX_INPUT_LENGTH} characters.")
    return None


# ---------------------------------------------------------------------------
# 2. DOMAIN RESTRICTION: allow only restaurant-related questions
#    Approach: keyword matching. Simple, fast, free (no API call).
#    Limitation: "How many people live in India?" contains "people" and passes.
#    (A stronger version would ask a small LLM to classify the message.)
# ---------------------------------------------------------------------------
DOMAIN_KEYWORDS = {
    "restaurant", "restaurants", "food", "eat", "eating", "dine", "dining",
    "dinner", "lunch", "breakfast", "brunch", "cuisine", "cuisines", "menu",
    "table", "tables", "reservation", "reservations", "reserve", "book",
    "booking", "guest", "guests", "people", "person", "persons", "pax",
    "cost", "costs", "price", "prices", "bill", "expensive", "cheap",
    "budget", "seat", "seats", "seating", "available", "availability",
    "veg", "vegetarian", "calculate", "estimate", "estimated",
}

# 3. CONTEXT HANDLING: short follow-ups like "yes", "no", "6", "make that 6"
#    have no restaurant keyword, but they're fine IF a conversation is ongoing.
FOLLOW_UP_PATTERNS = [
    re.compile(r"^(yes|yeah|yep|yup|no|nope|nah|ok|okay|sure|please|thanks|"
               r"thank you|go ahead|sounds good|great|perfect)\b", re.I),
    re.compile(r"^\d+(\s*(people|persons|guests|pax))?[.!]?$", re.I),
    re.compile(r"^(make (it|that)|what if|how about|and|also|instead|same)\b", re.I),
]


def is_follow_up(text: str) -> bool:
    text = text.strip()
    return any(p.search(text) for p in FOLLOW_UP_PATTERNS)


def is_restaurant_related(text: str, has_context: bool, known_terms=()) -> bool:
    """
    has_context: True if this conversation already has earlier turns.
    known_terms: restaurant names, cuisines, locations and IDs from the JSON,
                 so "Tell me about Spice Garden" passes even without a keyword.
    """
    lowered = text.lower()
    words = set(re.findall(r"[a-z]+", lowered))

    if words & DOMAIN_KEYWORDS:                       # set intersection
        return True
    if any(term in lowered for term in known_terms):
        return True
    if has_context and is_follow_up(text):
        return True
    return False


# ---------------------------------------------------------------------------
# 4. TOOL VALIDATION: guest count must be 1-20
#    Called from INSIDE the tool (tools.py). Returning a message instead of
#    raising an exception lets the model read the error and explain it nicely.
# ---------------------------------------------------------------------------
def validate_guest_count(guests: int) -> str | None:
    if guests < MIN_GUESTS:
        return f"Invalid guest count ({guests}). There must be at least {MIN_GUESTS} guest."
    if guests > MAX_GUESTS:
        return (f"Invalid guest count ({guests}). This assistant supports a maximum "
                f"of {MAX_GUESTS} guests per estimate.")
    return None


# ---------------------------------------------------------------------------
# 5. PII DETECTION and 6. OUTPUT REDACTION
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Phones are messy (+91 98765 43210, (040) 2345-6789, 9876543210...).
# Step 1: find "digit-ish" runs.  Step 2: keep only runs with 10-13 digits.
# This avoids redacting prices like "4,800" or IDs like "R101".
PHONE_CANDIDATE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def _find_phones(text: str) -> list[str]:
    return [m for m in PHONE_CANDIDATE_RE.findall(text)
            if 10 <= sum(ch.isdigit() for ch in m) <= 13]


def detect_pii(text: str) -> dict[str, list[str]]:
    """Returns e.g. {"email address": ["john@example.com"]}; empty dict if none."""
    found = {}
    emails = EMAIL_RE.findall(text)
    phones = _find_phones(text)
    if emails:
        found["email address"] = emails
    if phones:
        found["phone number"] = phones
    return found


def redact_pii(text: str) -> str:
    text = EMAIL_RE.sub("[EMAIL REDACTED]", text)       # emails first
    for phone in _find_phones(text):
        text = text.replace(phone, "[PHONE REDACTED]")
    return text


# ---------------------------------------------------------------------------
# Self-test: run  python guardrails.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("validate_input('')        ->", validate_input(""))
    print("validate_input('x'*600)   ->", validate_input("x" * 600))
    print("domain: Indian restaurants ->", is_restaurant_related("Show me Indian restaurants", False))
    print("domain: largest mammal     ->", is_restaurant_related("What is the largest mammal?", False))
    print("follow-up 'yes', no context ->", is_restaurant_related("yes", has_context=False))
    print("follow-up 'yes', context    ->", is_restaurant_related("yes", has_context=True))
    print("guests 0  ->", validate_guest_count(0))
    print("guests 50 ->", validate_guest_count(50))
    print("guests 6  ->", validate_guest_count(6))
    sample = "Email john@example.com or call +91 98765 43210. Total is 4,800."
    print("detect ->", detect_pii(sample))
    print("redact ->", redact_pii(sample))
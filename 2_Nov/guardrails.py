"""Layered guardrails for the Simple Python RAG project.

INPUT guardrails (run before retrieval):
  1. Basic validation      - empty / too long
  2. PII detection         - email, phone, PAN, Aadhaar, card, employee ID
  3. Encoded payloads      - Base64 text hiding instructions
  4. Prompt injection      - normalised text + flexible patterns (not exact phrases)
  5. Sensitive data        - salaries, home addresses, other people's records
  6. Harmful intent        - bypassing security, accessing others' accounts

RETRIEVAL guardrail:
  7. Relevance threshold   - refuse when the best chunk is too far away (off-topic)

OUTPUT guardrails (run on the AI answer):
  8. PII redaction
  9. System-prompt leak detection
 10. Number grounding      - every number in the answer must appear in the context

These are still classroom-level defences. They are much stronger than exact
keyword matching, but they are not a replacement for a moderation model,
access control on the documents, and human review.
"""
import base64
import re
import unicodedata
from dataclasses import dataclass

MAX_QUESTION_LENGTH = 300

# Cosine distance of the best retrieved chunk. Measured on this project's documents:
# policy questions score <= 0.73, off-topic questions score >= 0.85.
RELEVANCE_THRESHOLD = 0.80

REFUSAL_MESSAGE = "I cannot find the answer in the provided documents."


@dataclass
class GuardrailResult:
    allowed: bool
    layer: str
    reason: str


# =====================================================
# PATTERNS
# =====================================================

PII_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "card number": re.compile(r"(?<!\d)(?:\d[ -]?){12,15}\d(?!\d)"),
    "Aadhaar number": re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)"),
    "PAN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "employee ID": re.compile(
        r"\b(?:employee|emp|staff)\s*(?:id|no\.?|number|code)\s*(?:is|:|#|-)?\s*[A-Z0-9-]*\d[A-Z0-9-]*\b",
        re.IGNORECASE,
    ),
}

INJECTION_PATTERNS = [
    # "ignore / disregard / forget ... (up to 4 words) ... instructions / rules"
    re.compile(r"\b(ignore|disregard|forget|override|skip|drop)\b(\s+\S+){0,4}?\s+"
               r"(instructions?|rules?|prompts?|guidelines?|directions?|context|guardrails?)\b"),
    re.compile(r"\b(forget|ignore|disregard)\s+(everything|anything|all)\b"),
    re.compile(r"\b(system|hidden|initial|original|developer|secret)\s+"
               r"(prompt|instructions?|message|rules|configuration)\b"),
    re.compile(r"\bpretend\b|\bact as\b|\byou are now\b|\bfrom now on,? you\b|\brole-?play\b"),
    re.compile(r"\b(jailbreak|developer mode|dan mode|do anything now)\b"),
    re.compile(r"\bdecode\b.{0,30}\b(follow|execute|obey|run)\b"),
]

SENSITIVE_PATTERNS = [
    re.compile(r"\b(salar(y|ies)|pay ?slips?|compensation of|bonus(es)? of)\b"),
    re.compile(r"\b(home|personal|residential) (address(es)?|phone|number)\b"),
    re.compile(r"\b(bank (account|details)|medical (records?|history)|performance reviews?)\b"),
    re.compile(r"\b(aadhaar|pan) (card|number|details)\b"),
]

HARMFUL_PATTERNS = [
    re.compile(r"\b(bypass|disable|evade|circumvent|get around|turn off)\b.{0,40}"
               r"\b(vpn|monitor\w*|security|firewall|antivirus|mfa|2fa|logging|tracking|filter\w*)\b"),
    re.compile(r"\bwithout (them|him|her|anyone|their|my manager|it|it team) "
               r"(knowing|noticing|finding out|permission|consent)\b"),
    re.compile(r"\b(hack(ing|ed)?|steal(ing)?|phish(ing)?|keylog\w*|spy on|malware|ransomware)\b"),
    re.compile(r"\bcrack(ing)? (a |the |their |his |her )?passwords?\b"),
    re.compile(r"\b(access|log ?in ?to|get into|break into|read)\b.{0,30}"
               r"\b(co-?worker|colleague|someone else|another (employee|user|person))'?s?\b"),
    re.compile(r"\b(someone|co-?worker|colleague|another (employee|user)|manager)'?s? passwords?\b"),
]

# Phrases from the system prompt in main.py. If they appear in an answer,
# the model is probably leaking its instructions.
SYSTEM_PROMPT_MARKERS = [
    "you are a company policy question-answering assistant",
    "use only the supplied context",
    "do not use outside knowledge",
    "do not invent or assume information",
    "preserve exact numbers, dates and time periods",
]

NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15",
    "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
    "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
}

ZERO_WIDTH = re.compile(r"[​-‏⁠﻿]")
LEET_MAP = str.maketrans("013457@$", "oieastas")


# =====================================================
# HELPERS
# =====================================================

def normalize_text(text: str) -> str:
    """Lowercase, remove hidden characters, collapse spaces, join s p a c e d letters."""
    text = unicodedata.normalize("NFKC", text)
    text = ZERO_WIDTH.sub("", text).lower()
    text = re.sub(r"\s+", " ", text).strip()
    # "i g n o r e" -> "ignore"
    text = re.sub(r"\b(?:[a-z] ){2,}[a-z]\b", lambda m: m.group(0).replace(" ", ""), text)
    return text


def _matches_any(patterns, text: str) -> bool:
    return any(p.search(text) for p in patterns)


def _looks_like_injection(text: str) -> bool:
    normal = normalize_text(text)
    return _matches_any(INJECTION_PATTERNS, normal) or _matches_any(
        INJECTION_PATTERNS, normal.translate(LEET_MAP)
    )


def _decode_base64_tokens(text: str) -> list[str]:
    """Return readable text hidden in Base64-looking tokens."""
    decoded = []
    for token in re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", text):
        try:
            raw = base64.b64decode(token + "=" * (-len(token) % 4), validate=True)
            plain = raw.decode("utf-8")
        except Exception:
            continue
        printable = sum(ch.isprintable() for ch in plain) / max(len(plain), 1)
        if printable > 0.9 and re.search(r"[a-zA-Z]{3,}", plain):
            decoded.append(plain)
    return decoded


def _extract_numbers(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower())
    numbers = {NUMBER_WORDS[w] for w in words if w in NUMBER_WORDS}
    numbers.update(n.lstrip("0") or "0" for n in re.findall(r"\d+", text))
    return numbers


# =====================================================
# INPUT GUARDRAILS
# =====================================================

def check_input(question: str) -> GuardrailResult:
    if not question or not question.strip():
        return GuardrailResult(False, "validation", "Question is empty")

    if len(question) > MAX_QUESTION_LENGTH:
        return GuardrailResult(
            False, "validation", f"Question is longer than {MAX_QUESTION_LENGTH} characters"
        )

    for label, pattern in PII_PATTERNS.items():
        if pattern.search(question):
            return GuardrailResult(False, "pii", f"Personal data found ({label})")

    hidden = _decode_base64_tokens(question)
    if hidden:
        reason = "Encoded prompt injection" if any(map(_looks_like_injection, hidden)) \
            else "Encoded (Base64) text is not allowed"
        return GuardrailResult(False, "encoding", reason)

    if _looks_like_injection(question):
        return GuardrailResult(False, "injection", "Possible prompt-injection attempt")

    normal = normalize_text(question)

    if _matches_any(SENSITIVE_PATTERNS, normal):
        return GuardrailResult(False, "sensitive", "Request for confidential or personal data")

    if _matches_any(HARMFUL_PATTERNS, normal):
        return GuardrailResult(False, "harmful", "Request to bypass security or access others' data")

    return GuardrailResult(True, "input", "Passed all input guardrails")


# =====================================================
# RETRIEVAL GUARDRAIL
# =====================================================

def check_relevance(best_distance: float, threshold: float = RELEVANCE_THRESHOLD) -> GuardrailResult:
    if best_distance > threshold:
        return GuardrailResult(
            False, "relevance",
            f"Off-topic: best chunk distance {best_distance:.3f} > threshold {threshold}",
        )
    return GuardrailResult(
        True, "relevance", f"On-topic: best chunk distance {best_distance:.3f}"
    )


# =====================================================
# OUTPUT GUARDRAILS
# =====================================================

def redact_pii(text: str) -> str:
    for label, pattern in PII_PATTERNS.items():
        text = pattern.sub(f"[REDACTED {label.upper()}]", text)
    return text


def check_output(answer: str, context: str) -> tuple[str, list[str]]:
    """Return (safe_answer, warnings)."""
    warnings = []
    lowered = answer.lower()

    if any(marker in lowered for marker in SYSTEM_PROMPT_MARKERS):
        return REFUSAL_MESSAGE, ["System-prompt leak detected; answer replaced"]

    redacted = redact_pii(answer)
    if redacted != answer:
        warnings.append("Personal data redacted from answer")

    if REFUSAL_MESSAGE.lower() not in lowered:
        unsupported = sorted(_extract_numbers(redacted) - _extract_numbers(context), key=int)
        if unsupported:
            warnings.append(
                "Numbers not found in source documents: " + ", ".join(unsupported)
                + " (possible hallucination)"
            )

    return redacted, warnings

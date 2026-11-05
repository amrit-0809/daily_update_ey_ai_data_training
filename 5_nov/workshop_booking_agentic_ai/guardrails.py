
import re


# Detect email addresses
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Detect phone numbers
PHONE_PATTERN = re.compile(
    r"(?<!\d)\+?\d[\d\s().-]{7,}\d(?!\d)"
)


def contains_pii(text: str) -> bool:
    """Check whether text contains email or phone information."""

    if not isinstance(text, str):
        return False

    return bool(
        EMAIL_PATTERN.search(text)
        or PHONE_PATTERN.search(text)
    )


def clean_output(text: str) -> str:
    """Remove email addresses and phone numbers from output."""

    if not isinstance(text, str):
        return str(text)

    text = EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)

    text = PHONE_PATTERN.sub("[PHONE REDACTED]", text)

    return text

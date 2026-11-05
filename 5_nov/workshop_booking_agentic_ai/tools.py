
import json
from pathlib import Path
from langchain.tools import tool


BASE_DIR = Path(__file__).parent

WORKSHOP_FILE = BASE_DIR / "workshops.json"
COUPON_FILE = BASE_DIR / "coupons.json"


# Load workshop data
def get_workshops():
    data = json.loads(
        WORKSHOP_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(data, list):
        raise ValueError("Invalid workshop JSON format.")

    return data


# Load coupon data
def get_coupons():
    data = json.loads(
        COUPON_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(data, list):
        raise ValueError("Invalid coupon JSON format.")

    return data


# Validate workshop records
def find_workshop(workshop_id):
    for workshop in get_workshops():
        if workshop["id"] == workshop_id:
            return workshop

    return None


# Validate coupon
def validate_coupon(coupon_code):
    if not coupon_code:
        return None

    matches = [
        coupon for coupon in get_coupons()
        if coupon["coupon_code"].strip().upper()
        == coupon_code.strip().upper()
        and coupon.get("active") is True
    ]

    if len(matches) > 1:
        raise ValueError("Duplicate coupon codes detected.")

    if not matches:
        return None

    coupon = matches[0]

    if coupon.get("discount_type") != "percentage":
        raise ValueError("Unsupported discount type.")

    discount_value = coupon.get("discount_value")

    if (
        isinstance(discount_value, bool)
        or not isinstance(discount_value, (int, float))
        or not 0 < discount_value <= 100
    ):
        raise ValueError("Invalid coupon discount percentage.")

    return coupon


# TOOL 1: List all workshops
@tool
def list_all_workshops() -> str:
    """List all currently available workshops with their fees."""

    workshops = [
        w for w in get_workshops()
        if w.get("available") is True
    ]

    return json.dumps(workshops, indent=2)


# TOOL 2: Search workshops
@tool
def search_workshops(keyword: str) -> str:
    """Search available workshops by title."""

    if not keyword.strip():
        return "Please provide a workshop search keyword."

    matches = [
        w for w in get_workshops()
        if w.get("available") is True
        and keyword.lower() in w["title"].lower()
    ]

    if not matches:
        return "No matching workshops found."

    return json.dumps(matches, indent=2)


# TOOL 3: Find cheapest workshop
@tool
def find_cheapest_workshop() -> str:
    """Find the cheapest currently available workshop."""

    workshops = [
        w for w in get_workshops()
        if w.get("available") is True
    ]

    if not workshops:
        return "No workshops currently available."

    cheapest = min(
        workshops,
        key=lambda w: w["fee"]
    )

    return json.dumps({
        "workshop_id": cheapest["id"],
        "workshop": cheapest["title"],
        "fee": cheapest["fee"]
    }, indent=2)


# TOOL 4: Calculate workshop fee and coupon discount
@tool
def calculate_workshop_fee(
    workshop_id: str,
    participants: int,
    coupon_code: str = ""
) -> str:
    """
    Calculate total workshop fees.
    Apply a valid coupon discount if provided.
    Participant count must be between 1 and 30.
    """

    if (
        isinstance(participants, bool)
        or not isinstance(participants, int)
        or participants < 1
        or participants > 30
    ):
        return "Participant count must be between 1 and 30."

    workshop = find_workshop(workshop_id)

    if not workshop:
        return "Workshop not found."

    if workshop.get("available") is not True:
        return "This workshop is currently unavailable."

    fee = workshop.get("fee")

    if (
        isinstance(fee, bool)
        or not isinstance(fee, (int, float))
        or fee < 0
    ):
        return "Invalid workshop fee."

    subtotal = round(fee * participants, 2)

    discount = 0
    coupon_status = "Not provided"
    applied_coupon = None

    if coupon_code.strip():

        coupon = validate_coupon(coupon_code)

        if coupon:
            discount = round(
                subtotal * coupon["discount_value"] / 100,
                2
            )

            coupon_status = "Applied"
            applied_coupon = coupon["coupon_code"]

        else:
            coupon_status = "Invalid or inactive coupon"

    final_total = round(subtotal - discount, 2)

    return json.dumps({
        "workshop_id": workshop["id"],
        "workshop": workshop["title"],
        "participants": participants,
        "price_per_person": fee,
        "subtotal": subtotal,
        "coupon_code": applied_coupon,
        "coupon_status": coupon_status,
        "discount_percentage": (
            coupon["discount_value"] if coupon_status == "Applied"
            else 0
        ),
        "discount_amount": discount,
        "final_total": final_total
    }, indent=2)

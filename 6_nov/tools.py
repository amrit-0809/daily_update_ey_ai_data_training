
import json
from pathlib import Path

from langchain.tools import tool

from guardrails import validate_guest_count

# Path relative to THIS file, so it works no matter which folder you run from
DATA_FILE = Path(__file__).parent / "restaurants.json"

# Words to ignore when searching, so "Indian restaurants" still matches "Indian"
STOP_WORDS = {"restaurant", "restaurants", "food", "cuisine", "place", "places",
              "in", "at", "the", "a", "show", "me", "find"}


def load_restaurants() -> list[dict]:
    """Read restaurants.json. Works with a plain list or {"restaurants": [...]}."""
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("restaurants", [])
    return data


def _format(r: dict) -> str:
    return (f"{r['id']} | {r['name']} | {r['cuisine']} | {r['location']} | "
            f"₹{r['price_per_person']} per person | {r['available_seats']} seats available")


# ---------------------------------------------------------------------------
# TOOL 1
# ---------------------------------------------------------------------------
@tool
def search_restaurants(query: str) -> str:
    """Search restaurants by cuisine type, restaurant name, or location.

    Use this when the user wants to find or browse restaurants, or when you
    need a restaurant's ID before calculating a cost.

    Args:
        query: A cuisine (e.g. "Indian"), part of a restaurant name, or a
               location. Use "all" to list every restaurant.
    """
    restaurants = load_restaurants()
    words = [w for w in query.lower().split() if w not in STOP_WORDS]

    if not words or words == ["all"]:
        matches = restaurants
    else:
        # A restaurant matches if EVERY search word appears somewhere in it
        matches = []
        for r in restaurants:
            haystack = f"{r['name']} {r['cuisine']} {r['location']}".lower()
            if all(w in haystack for w in words):
                matches.append(r)

    if not matches:
        cuisines = sorted({r["cuisine"] for r in restaurants})
        return (f"No restaurants found matching '{query}'. "
                f"Available cuisines: {', '.join(cuisines)}.")

    lines = [f"Found {len(matches)} restaurant(s):"] + [_format(r) for r in matches]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# TOOL 2
# ---------------------------------------------------------------------------
@tool
def calculate_dining_cost(restaurant_id: str, guests: int) -> str:
    """Calculate the estimated total dining cost for a group at one restaurant.

    Always pass the guest count exactly as the user stated it; this tool
    validates it. If you only know the restaurant's name, call
    search_restaurants first to get its ID.

    Args:
        restaurant_id: The restaurant's ID, e.g. "R101".
        guests: Number of guests.
    """
    # TOOL GUARDRAIL: validate before doing anything else
    error = validate_guest_count(guests)
    if error:
        return error

    rid = restaurant_id.strip().upper()
    restaurant = next((r for r in load_restaurants() if str(r["id"]).upper() == rid), None)
    if restaurant is None:
        return (f"No restaurant exists with ID '{restaurant_id}'. "
                f"Use search_restaurants to find valid IDs.")

    price = restaurant["price_per_person"]
    total = price * guests
    msg = (f"Estimated cost at {restaurant['name']} ({restaurant['id']}): "
           f"{guests} guests x ₹{price} = ₹{total:,}.")
    if guests > restaurant["available_seats"]:
        msg += f" Note: only {restaurant['available_seats']} seats are currently available."
    return msg + " (Estimate only. No booking has been made.)"


# ---------------------------------------------------------------------------
# Self-test: python tools.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # After @tool, these are Tool OBJECTS, not plain functions.
    # You call them with .invoke() and a dict of arguments.
    print(search_restaurants.invoke({"query": "Indian"}))
    print()
    print(calculate_dining_cost.invoke({"restaurant_id": "R101", "guests": 4}))
    print(calculate_dining_cost.invoke({"restaurant_id": "R101", "guests": 50}))
    print(calculate_dining_cost.invoke({"restaurant_id": "R999", "guests": 2}))
    print()
    # This is what the model "sees" about each tool:
    print("Tool name:", search_restaurants.name)
    print("Tool args:", calculate_dining_cost.args)
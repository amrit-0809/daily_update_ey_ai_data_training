
import os
import uuid

from dotenv import load_dotenv

load_dotenv()  # Must run before the model client is created, so it can find OPENROUTER_API_KEY

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

import guardrails as gr
from tools import calculate_dining_cost, load_restaurants, search_restaurants

# ---------------------------------------------------------------------------
# SYSTEM PROMPT: the agent's "job description". Note the anti-hallucination rules.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a Restaurant Reservation Assistant.

You help users find restaurants and estimate dining costs. Rules:
1. Only discuss restaurants: finding them, cuisines, locations, prices,
   seat availability and estimated dining costs.
2. NEVER invent restaurant names, IDs, cuisines, prices or availability.
   Use ONLY information returned by your tools. If a search finds nothing,
   say so plainly.
3. Use search_restaurants to find restaurants.
4. Use calculate_dining_cost to estimate costs. It needs the restaurant ID.
   If you don't already know the ID from this conversation, call
   search_restaurants first to get it.
5. Remember the restaurant and guest count from earlier in the conversation.
   For follow-ups like "make that 6 people", reuse the previously selected
   restaurant.
6. Always pass the guest count to the tool exactly as the user stated it,
   even if it looks invalid. The tool validates it. Relay any error it returns.
7. You cannot make bookings or take payments. If asked, explain that you
   only provide restaurant information and cost estimates.
8. Never ask for or repeat email addresses or phone numbers.
9. Keep answers short and clear. Prices are in Indian Rupees (₹).
"""


def build_agent():
    # OpenRouter speaks the same API format as OpenAI ("OpenAI-compatible"),
    # so we reuse ChatOpenAI and just point it at a different server + key.
    # The model is read from .env so you can swap free models without editing code.
    model = ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "openrouter/free"),
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        temperature=0,  # more consistent answers, which helps with tool use
    )

    return create_agent(
        model=model,
        tools=[search_restaurants, calculate_dining_cost],  # register both tools
        system_prompt=SYSTEM_PROMPT,
        # MEMORY: the checkpointer saves every thread's message history.
        # Each conversation is identified by a thread_id (see run_turn).
        checkpointer=InMemorySaver(),
    )


def build_known_terms() -> set[str]:
    """Names, cuisines, locations and IDs from the JSON, for the domain guardrail."""
    terms = set()
    for r in load_restaurants():
        terms.update({str(r["id"]).lower(), r["name"].lower(),
                      r["cuisine"].lower(), r["location"].lower()})
    return terms


def run_turn(agent, text: str, thread_id: str) -> str:
    # The thread_id tells the checkpointer WHICH conversation's history to load.
    # Same thread_id -> the agent remembers. New thread_id -> blank slate.
    config = {"configurable": {"thread_id": thread_id}}

    # We send ONLY the new message. The checkpointer adds the earlier history.
    result = agent.invoke({"messages": [{"role": "user", "content": text}]}, config=config)

    # result["messages"] is the WHOLE thread (proof that memory works!).
    # Find where THIS turn began so we only print this turn's tool calls.
    messages = result["messages"]
    start = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))

    for m in messages[start + 1:]:
        if isinstance(m, AIMessage) and m.tool_calls:
            # The model DECIDED to call a tool. It doesn't run it; LangChain does.
            for call in m.tool_calls:
                print(f"  [TOOL SELECTED] {call['name']}  args={call['args']}")
        elif isinstance(m, ToolMessage):
            preview = m.content.replace("\n", " | ")
            print(f"  [TOOL RESULT]   {preview[:150]}{'...' if len(preview) > 150 else ''}")

    return messages[-1].content  # the final AI answer


def main():
    agent = build_agent()
    known_terms = build_known_terms()
    thread_id = str(uuid.uuid4())
    turns = 0  # completed turns in the current conversation (used for follow-ups)

    print("Restaurant AI Assistant")
    print("Commands: /new = fresh conversation, /quit = exit\n")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        command = user_input.lower()
        if command in {"/quit", "/exit"}:
            print("Goodbye!")
            break
        if command == "/new":
            # A new thread_id means the checkpointer has no history for it.
            # (The old thread still exists in RAM, but we no longer point at it.)
            thread_id = str(uuid.uuid4())
            turns = 0
            print("[NEW] Started a fresh conversation. Previous details are no longer available.")
            continue

        # ---- INPUT GUARDRAIL 1: empty / too long ----
        error = gr.validate_input(user_input)
        if error:
            print(f"[GUARDRAIL: input] {error}")
            continue

        # ---- INPUT GUARDRAIL 2: PII detection (redact BEFORE it reaches the AI) ----
        pii = gr.detect_pii(user_input)
        if pii:
            print(f"[GUARDRAIL: PII] Detected {', '.join(pii)}. "
                  f"It was redacted and not sent to the AI.")
            user_input = gr.redact_pii(user_input)

        # ---- INPUT GUARDRAIL 3: domain restriction (+ follow-up context) ----
        if not gr.is_restaurant_related(user_input, has_context=turns > 0,
                                        known_terms=known_terms):
            if pii:
                print("Assistant: No need to share contact details. I only provide "
                      "restaurant information and cost estimates; I don't make bookings.")
            else:
                print("[GUARDRAIL: domain] Sorry, I can only help with restaurant-related "
                      "questions (finding restaurants, prices, seats, dining costs).")
            continue

        # ---- THE AGENT ----
        try:
            reply = run_turn(agent, user_input, thread_id)
        except Exception as e:  # network/API key problems, etc.
            print(f"[ERROR] Could not reach the AI: {e}")
            continue
        turns += 1

        # ---- OUTPUT GUARDRAIL: redact PII in the model's answer ----
        safe_reply = gr.redact_pii(reply)
        if safe_reply != reply:
            print("[GUARDRAIL: output] PII was redacted from the response.")
        print(f"\nAssistant: {safe_reply}")


if __name__ == "__main__":
    main()
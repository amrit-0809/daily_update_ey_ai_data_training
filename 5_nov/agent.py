"""AI Library Assistant: the model decides which Python tool to run (via OpenRouter)."""

import json
import os

from dotenv import load_dotenv
from openai import APIError, AuthenticationError, OpenAI

from tools import TOOLS, TOOL_FUNCTIONS

load_dotenv()

MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = """You are a friendly AI Library Assistant.
You can search the library catalogue and reserve books for customers using your tools.
- Always use search_books to look up books; never invent books or availability.
- To reserve a book you need its ID and the customer's name. If only a title is given, search first.
- If the customer's name is missing, ask for it before reserving.
- If a book has no available copies, do not try to reserve it; tell the user and suggest alternatives.
- If the user asks to reserve "a book with no available copies", search the catalogue, identify such a book,
  and explain that it cannot be reserved.
Keep answers short and clear."""

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


def parse_args(arguments: str) -> dict:
    try:
        return json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return {}


def run_tool(name: str, arguments: str, **extra) -> str:
    """Execute the Python function the model selected and return its result as JSON."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return json.dumps(func(**parse_args(arguments), **extra))
    except Exception as e:  # report tool errors back to the model
        return json.dumps({"error": str(e)})


def model_turn(messages: list) -> tuple:
    """Ask the model what to do next.

    Appends the assistant message to `messages` and returns (text, tool_calls),
    where tool_calls is a list of {"id", "name", "arguments"} dicts (empty = final answer).
    """
    # Steps 2-3: give the model the tools and let it decide
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )
    message = response.choices[0].message
    text = message.content or ""

    if not message.tool_calls:
        messages.append({"role": "assistant", "content": text})
        return text, []

    calls = [
        {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
        for tc in message.tool_calls
    ]
    # Keep the assistant's tool-call request in the history
    messages.append(
        {
            "role": "assistant",
            "content": text,
            "tool_calls": [
                {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in calls
            ],
        }
    )
    return text, calls


def add_tool_result(messages: list, call: dict, result: str) -> None:
    """Step 5: send the tool result back to the model."""
    messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})


def ask_agent(messages: list) -> str:
    """Run the agent loop (terminal version) until the model gives a final answer."""
    for _ in range(MAX_TOOL_ROUNDS):
        text, calls = model_turn(messages)
        if not calls:
            return text or "(no response)"  # Step 6: final answer

        # Step 4: execute each selected Python function
        for call in calls:
            print(f"  [Agent selected tool] {call['name']}({call['arguments']})")
            result = run_tool(call["name"], call["arguments"])
            print(f"  [Tool result] {result}")
            add_tool_result(messages, call, result)

    return "Sorry, I couldn't complete that request. Please try rephrasing it."


def main():
    if not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY is missing. Add it to the .env file.")
        return

    print("=" * 60)
    print(f" AI Library Assistant  (model: {MODEL})")
    print(" Type 'exit' to quit.")
    print("=" * 60)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            break

        turn_start = len(messages)
        messages.append({"role": "user", "content": question})
        try:
            answer = ask_agent(messages)
        except AuthenticationError:
            print("Invalid API key. Check OPENROUTER_API_KEY in the .env file.")
            del messages[turn_start:]
            continue
        except APIError as e:
            print(f"API error: {e}")
            del messages[turn_start:]
            continue

        print(f"\nAssistant: {answer}")

    print("Goodbye!")


if __name__ == "__main__":
    main()

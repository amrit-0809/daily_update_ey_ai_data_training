"""Web UI for the AI Library Assistant.  Run with:  streamlit run app.py"""

import json

import streamlit as st
from openai import APIError, AuthenticationError

from agent import (
    MAX_TOOL_ROUNDS,
    MODEL,
    SYSTEM_PROMPT,
    add_tool_result,
    model_turn,
    parse_args,
    run_tool,
)
from tools import check_reservable, load_books, load_reservations

st.set_page_config(page_title="AI Library Assistant", page_icon=":material/local_library:", layout="wide")

SUGGESTIONS = {
    ":material/code: Python books": "Find books related to Python programming.",
    ":material/search: Is Python Crash Course available?": "Is Python Crash Course available?",
    ":material/bookmark_add: Reserve for Ahmed": "Reserve Python Crash Course for Ahmed.",
    ":material/psychology: AI books": "Show me books related to artificial intelligence.",
    ":material/block: Reserve an unavailable book": "Reserve a book that has no available copies.",
}
TOOL_ICONS = {"search_books": ":material/search:", "reserve_book": ":material/bookmark_add:"}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def reset_chat():
    st.session_state.history = [{"role": "system", "content": SYSTEM_PROMPT}]  # sent to the model
    st.session_state.display = []  # what the chat shows
    st.session_state.pending = None  # reservation waiting for Confirm / Cancel
    st.session_state.error = None
    st.session_state.pop("suggestion", None)


if "history" not in st.session_state:
    reset_chat()
ss = st.session_state


# ---------------------------------------------------------------------------
# Agent driver (pauses when a reservation needs the user's approval)
# ---------------------------------------------------------------------------
def drive(steps: list, calls: list, rounds: int) -> None:
    """Run tool calls and model turns until a final answer, or pause for confirmation."""
    while True:
        while calls:
            call = calls[0]
            if call["name"] == "reserve_book":
                args = parse_args(call["arguments"])
                book, error = check_reservable(args.get("book_id"))
                if error is None:  # reservable -> ask the user first
                    ss.pending = {
                        "calls": calls,
                        "steps": steps,
                        "rounds": rounds,
                        "book": book,
                        "customer": args.get("customer_name", ""),
                    }
                    return
            result = run_tool(call["name"], call["arguments"])
            add_tool_result(ss.history, call, result)
            steps.append({"name": call["name"], "arguments": call["arguments"], "result": result})
            calls.pop(0)

        if rounds >= MAX_TOOL_ROUNDS:
            final = "Sorry, I couldn't complete that request. Please try rephrasing it."
            break
        text, calls = model_turn(ss.history)
        rounds += 1
        if not calls:
            final = text or "(no response)"
            break

    ss.display.append({"role": "assistant", "content": final, "steps": steps})


def safely(fn, *args):
    """Run an agent step; on API errors roll the conversation back to before this question."""
    try:
        fn(*args)
    except AuthenticationError:
        ss.error = "Invalid API key. Check OPENROUTER_API_KEY in the .env file."
    except APIError as e:
        ss.error = f"API error: {e}"
    else:
        return
    ss.history = ss.history[: ss.turn_start]
    ss.display = ss.display[: ss.display_start]
    ss.pending = None


def start_turn(question: str) -> None:
    ss.error = None
    ss.turn_start, ss.display_start = len(ss.history), len(ss.display)
    ss.history.append({"role": "user", "content": question})
    ss.display.append({"role": "user", "content": question})
    drive([], [], 0)


def resolve_pending(approved: bool) -> None:
    p, ss.pending = ss.pending, None
    call = p["calls"].pop(0)
    result = run_tool(call["name"], call["arguments"], confirm=lambda *_: approved)
    add_tool_result(ss.history, call, result)
    p["steps"].append({"name": call["name"], "arguments": call["arguments"], "result": result})
    drive(p["steps"], p["calls"], p["rounds"])


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def render_steps(steps: list) -> None:
    for step in steps:
        with st.expander(f"Agent selected tool: `{step['name']}`", type="step", icon=TOOL_ICONS.get(step["name"])):
            st.caption("Arguments")
            st.json(parse_args(step["arguments"]))
            st.caption("Tool result")
            try:
                st.json(json.loads(step["result"]), expanded=False)
            except json.JSONDecodeError:
                st.code(step["result"])


# ---------------------------------------------------------------------------
# Sidebar: live library data
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header(":material/local_library: Library")
    st.caption(f"Model: `{MODEL}`")
    st.button(":material/refresh: New chat", on_click=reset_chat, width="stretch")

    books = load_books()
    st.subheader("Books")
    st.dataframe(
        books,
        hide_index=True,
        column_order=["id", "title", "available_copies"],
        column_config={
            "id": st.column_config.NumberColumn("ID", format="%d", width="small"),
            "title": st.column_config.TextColumn("Title"),
            "available_copies": st.column_config.NumberColumn("Copies", width="small"),
        },
        alt="Library books and available copies",
    )

    reservations = load_reservations()
    st.subheader(f"Reservations ({len(reservations)})")
    if reservations:
        st.dataframe(
            reservations,
            hide_index=True,
            column_order=["reservation_id", "title", "customer_name", "reserved_at"],
            column_config={
                "reservation_id": st.column_config.NumberColumn("#", format="%d", width="small"),
                "title": "Book",
                "customer_name": "Customer",
                "reserved_at": "Reserved at",
            },
            alt="Saved reservations",
        )
    else:
        st.caption("No reservations yet.")


# ---------------------------------------------------------------------------
# Main chat
# ---------------------------------------------------------------------------
st.title("AI Library Assistant")
st.caption("Ask about books or reserve one. The assistant picks the right tool for you.")

for msg in ss.display:
    with st.chat_message(msg["role"]):
        if msg.get("steps"):
            render_steps(msg["steps"])
        st.markdown(msg["content"])

if ss.error:
    st.error(ss.error, title="Something went wrong")

# Reservation waiting for approval
if ss.pending:
    p = ss.pending
    with st.chat_message("assistant"):
        render_steps(p["steps"])
        with st.container(border=True):
            st.markdown(f"**Confirm reservation**  \n**{p['book']['title']}** (ID {p['book']['id']}) "
                        f"for **{p['customer']}**  \n{p['book']['available_copies']} copies available")
            with st.container(horizontal=True):
                confirm = st.button(":material/check: Confirm", type="primary")
                cancel = st.button(":material/close: Cancel")
    if confirm or cancel:
        with st.spinner("Updating reservation..."):
            safely(resolve_pending, bool(confirm))
        st.rerun()

prompt = st.chat_input(
    "Confirm or cancel the reservation above first" if ss.pending else "Ask about books or reserve one...",
    disabled=bool(ss.pending),
    submit_mode="disable",
)

if not ss.display and not ss.pending:
    suggestions = st.empty()
    picked = suggestions.pills("Try asking:", list(SUGGESTIONS), key="suggestion")
    if picked:
        prompt = SUGGESTIONS[picked]
    if prompt:
        suggestions.empty()

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            safely(start_turn, prompt)
    st.rerun()

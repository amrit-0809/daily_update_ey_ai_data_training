
import asyncio
import json
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from typing_extensions import Never
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler, response_handler

load_dotenv()
AGENTS: dict = {}


# ---------- Config: connect to the agents created in the Foundry portal ----------
def connect_agents() -> dict:
    required = ["FOUNDRY_PROJECT_ENDPOINT", "ELIGIBILITY_AGENT", "RISK_AGENT", "CUSTOMER_AGENT"]
    missing = [k for k in required if not os.getenv(k, "").strip()]
    if missing:
        print(f"[CONFIG ERROR] Missing in .env: {', '.join(missing)}")
        print("Copy .env.example to .env, fill in your Foundry values, then run 'az login'.")
        sys.exit(1)

    from agent_framework.foundry import FoundryAgent
    from azure.identity import AzureCliCredential
    credential = AzureCliCredential()

    def agent(key: str):
        return FoundryAgent(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            agent_name=os.environ[key],
            agent_version=os.getenv(f"{key}_VERSION") or None,
            credential=credential,
        )
    return {"eligibility": agent("ELIGIBILITY_AGENT"), "risk": agent("RISK_AGENT"),
            "customer": agent("CUSTOMER_AGENT")}


async def ask(name: str, payload: dict) -> str:
    try:
        result = await AGENTS[name].run(json.dumps(payload, indent=2))
        return result.text.strip()
    except Exception as exc:
        print(f"  [warn] {name} agent failed: {type(exc).__name__}: {exc}")
        return ""


# ---------- Deterministic business rules 1-5 (field names match returns.json) ----------
def policy_issues(r: dict) -> list[str]:
    issues = []
    if not r["amount_inr"] < 25000:
        issues.append(f"Amount Rs.{r['amount_inr']:,} is not below Rs.25,000")
    if not r["days_since_delivery"] <= 30:
        issues.append(f"Requested {r['days_since_delivery']} days after delivery (limit 30)")
    if not r["invoice_available"]:
        issues.append("Invoice not available")
    condition = r["item_condition"].upper()
    if not (condition == "UNOPENED" or (condition == "DAMAGED" and r["photo_evidence_available"])):
        issues.append(f"Item condition '{condition}' is not unopened or damaged-with-photos")
    if not r["previous_returns_90_days"] < 3:
        issues.append(f"{r['previous_returns_90_days']} previous returns in 90 days (limit: fewer than 3)")
    return issues


# ---------- Message passed out of the workflow when it pauses ----------
@dataclass
class ManagerApproval:
    case: dict  # full context travels with the request


# ---------- Executors (graph nodes) ----------
class EligibilityExecutor(Executor):
    @handler
    async def run(self, request: dict, ctx: WorkflowContext[dict]) -> None:
        case = {"request": request, "issues": policy_issues(request)}
        case["eligibility"] = await ask("eligibility", {**request, "policy_issues": case["issues"]}) \
            or ("Eligible." if not case["issues"] else "Not eligible: " + "; ".join(case["issues"]))
        print(f"  Eligibility: {'PASS' if not case['issues'] else 'FAIL'}")
        await ctx.send_message(case)


class RiskExecutor(Executor):
    @handler
    async def run(self, case: dict, ctx: WorkflowContext[dict]) -> None:
        raw = await ask("risk", case["request"])
        try:
            data = json.loads(raw.replace("```json", "").replace("```", ""))
            case["risk_level"], case["risk"] = data["risk_level"].upper(), data["assessment"]
        except (ValueError, KeyError, AttributeError):
            case["risk_level"], case["risk"] = "HIGH", "Risk Agent unavailable - treated as HIGH (fail-safe)."
        print(f"  Risk: {case['risk_level']}")
        await ctx.send_message(case)


class ApprovalGateway(Executor):
    @handler
    async def run(self, case: dict, ctx: WorkflowContext[dict]) -> None:
        if case["risk_level"] == "HIGH":
            case["issues"].append("Risk Agent identified a HIGH-risk concern")  # rule 6
        if case["issues"]:
            case["route"] = "Human Review"
        else:
            case["route"], case["decision"] = "Automatic", "AUTO_APPROVED"
        print(f"  Route: {case['route']}")
        await ctx.send_message(case)


class HumanReview(Executor):
    @handler
    async def run(self, case: dict, ctx: WorkflowContext[dict]) -> None:
        print("  Paused for manager approval...")
        await ctx.request_info(request_data=ManagerApproval(case=case), response_type=str)

    @response_handler
    async def resume(self, original: ManagerApproval, answer: str, ctx: WorkflowContext[dict]) -> None:
        case = original.case
        case["decision"] = "MANAGER_APPROVED" if answer == "approve" else "MANAGER_REJECTED"
        print(f"  Resumed: {case['decision']}")
        await ctx.send_message(case)


class CustomerResponse(Executor):
    @handler
    async def run(self, case: dict, ctx: WorkflowContext[Never, dict]) -> None:
        r, decision = case["request"], case["decision"]
        verdict = "REJECTED" if decision == "MANAGER_REJECTED" else "APPROVED"
        request_type = r["request_type"].lower()
        msg = await ask("customer", {"order_id": r["order_id"], "product": r["product"],
                                     "request_type": request_type, "decision": verdict,
                                     "reasons": case["issues"]})
        banned = ["has been refunded", "has been processed", "has been credited", "has been issued",
                  "has been shipped", "has been dispatched", "refund is complete"]
        if verdict == "REJECTED":
            banned += ["has been approved", "is approved"]
        if not msg or any(b in msg.lower() for b in banned):  # AI can never change the decision
            msg = (f"Dear customer, your {request_type} request for order {r['order_id']} has been "
                   f"{'approved; our team will contact you with next steps' if verdict == 'APPROVED' else 'reviewed and could not be approved'}.")
        await ctx.yield_output({
            "request_id": r["request_id"], "order_id": r["order_id"],
            "product": r["product"], "requested_amount": r["amount_inr"],
            "eligibility_findings": case["eligibility"], "eligibility_issues": case["issues"],
            "risk_assessment": f"{case['risk_level']}: {case['risk']}",
            "approval_route": case["route"], "final_decision": decision,
            "customer_communication_draft": msg,
        })


# ---------- Workflow graph ----------
def build_workflow():
    eligibility, risk = EligibilityExecutor(id="eligibility"), RiskExecutor(id="risk")
    gateway, human, customer = ApprovalGateway(id="gateway"), HumanReview(id="human"), CustomerResponse(id="customer")
    return (WorkflowBuilder(start_executor=eligibility)
            .add_edge(eligibility, risk)
            .add_edge(risk, gateway)
            .add_edge(gateway, customer, condition=lambda c: c["route"] == "Automatic")
            .add_edge(gateway, human, condition=lambda c: c["route"] == "Human Review")
            .add_edge(human, customer)
            .build())


# ---------- Human-in-the-loop console ----------
def ask_manager(case: dict) -> str:
    r = case["request"]
    print(f"\n  ===== MANAGER APPROVAL: {r['request_id']} =====")
    print(f"  Item: {r['product']}   Amount: Rs.{r['amount_inr']:,}")
    print(f"  Eligibility issues: {case['issues']}")
    print(f"  Risk: {case['risk_level']} - {case['risk']}")
    while True:
        answer = input("  Enter approve or reject: ").strip().lower()
        if answer in ("approve", "reject"):
            return answer
        print(f"  Invalid input '{answer}'. Type exactly 'approve' or 'reject'.")


async def process(request: dict) -> dict:
    workflow, output = build_workflow(), None
    stream = workflow.run(request, stream=True)
    while True:
        pending = {}
        async for event in stream:
            if event.type == "request_info":
                pending[event.request_id] = ask_manager(event.data.case)
            elif event.type == "output":
                output = event.data
        if not pending:
            return output
        print("  Resuming workflow...")
        stream = workflow.run(stream=True, responses=pending)


async def main() -> None:
    AGENTS.update(connect_agents())
    with open("returns.json", encoding="utf-8") as f:
        requests = json.load(f)
    print(f"Loaded {len(requests)} requests. SIMULATION ONLY - no refunds or messages are executed.")

    results = []
    for request in requests:
        print(f"\n### {request['request_id']} | {request['product']}")
        result = await process(request)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        results.append(result)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nSUMMARY")
    for r in results:
        print(f"  {r['request_id']:<9}{r['approval_route']:<14}{r['final_decision']}")


if __name__ == "__main__":
    asyncio.run(main())
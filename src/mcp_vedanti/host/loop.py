"""ReAct loop for one equipment request.

One model call per step. The transcript grows with each thought, action, and observation.
"""

import json
from pathlib import Path
from typing import Protocol

from mcp_vedanti.host.adapter import ModelAdapter
from mcp_vedanti.host.client import EquipmentClient
from mcp_vedanti.host.extract import extract_prompt, parse_extract
from mcp_vedanti.host.prompt import agent_prompt
from mcp_vedanti.host.reflect import employee_reply, reflect
from mcp_vedanti.host.runlog import RUNS_DIR, format_event, format_run, run_path, write_run


class ToolCaller(Protocol):
    """The two host client calls the loop uses."""

    async def list_tools(self) -> list[dict]:
        """Return the tool catalog."""

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Return text and is_error for one tool call."""

STEP_LIMIT = 8
LOOKUP_TOOL = "get_employee_info"
POLICY_TOOL = "get_policy_limits"
ELIGIBILITY_TOOL = "check_request_eligibility"
FLAG_TOOL = "flag_for_human_review"
DECISIVE_STATUSES = {"in_policy", "out_of_policy"}
REVIEW_STATUSES = {"indeterminate", "not_found"}

PARSE_OBSERVATION = (
    "The reply was not one JSON object with a thought and either a tool "
    "or a draft."
)
NEED_REVIEW_OBSERVATION = "A review has to be filed before a reply."
NEED_STATUS_OBSERVATION = "Call check_request_eligibility before drafting."
ITEM_LOCKED_OBSERVATION = "The item is already bound. Use that item."
NO_ITEM_ELIGIBILITY_OBSERVATION = (
    "No single item is bound, so eligibility is not allowed."
)
NEED_LOOKUP_OBSERVATION = "Look up the employee before checking eligibility."
NEED_POLICY_OBSERVATION = (
    "Read the policy for that employee's role before checking eligibility."
)
EMPLOYEE_LOCKED_OBSERVATION = "The employee id is already bound. Use that id."
STEP_LIMIT_REPLY = (
    "I'm sorry, I could not finish this request. Please try again or contact IT."
)


def _flag_blocked_observation(status: str | None) -> str:
    """The sentence appended when a ticket call is not allowed."""
    if status is None:
        return "No classification status is available, so a ticket is not allowed."
    return f"Status {status} does not allow a ticket."


def _parse_reply(text: str) -> dict | None:
    """Return a thought plus a tool or a draft. Anything else is unusable."""
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict) or not isinstance(body.get("thought"), str):
        return None
    has_tool = "tool" in body
    has_draft = "draft" in body
    if has_tool == has_draft:
        return None
    if has_draft:
        if not isinstance(body["draft"], str):
            return None
        return {"thought": body["thought"], "draft": body["draft"]}
    if not isinstance(body["tool"], str):
        return None
    arguments = body.get("arguments", {})
    if not isinstance(arguments, dict):
        return None
    return {
        "thought": body["thought"],
        "tool": body["tool"],
        "arguments": arguments,
    }


def _status_from_eligibility(text: str) -> str | None:
    """Read a classification status out of a successful eligibility result."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict):
        return None
    status = body.get("status")
    if status in DECISIVE_STATUSES or status in REVIEW_STATUSES:
        return status
    return None


async def run_request(
    employee_id: str,
    query: str,
    adapter: ModelAdapter,
    *,
    client: ToolCaller | None = None,
    step_limit: int = STEP_LIMIT,
    run_dir: Path | None = RUNS_DIR,
    prompt: str = "1",
) -> dict:
    """Run one request. Prints the trace and writes the same text to one file."""
    if client is None:
        async with EquipmentClient() as connected:
            return await _run(
                employee_id,
                query,
                adapter,
                connected,
                step_limit,
                run_dir,
                prompt,
            )
    return await _run(
        employee_id, query, adapter, client, step_limit, run_dir, prompt
    )


async def _run(
    employee_id: str,
    query: str,
    adapter: ModelAdapter,
    client: ToolCaller,
    step_limit: int,
    run_dir: Path | None,
    prompt: str,
) -> dict:
    tools = await client.list_tools()
    bound_item = _bound_item(adapter, employee_id, query)
    messages = [
        {"role": "system", "content": agent_prompt(tools, prompt)},
        {"role": "user", "content": _react_user(employee_id, query, bound_item)},
    ]
    trace: list[dict] = []
    status: str | None = None
    ticket_filed = False
    looked_up = False
    employee_found = False
    record_role: str | None = None
    policy_ok = False

    for _ in range(step_limit):
        reply = adapter.complete(messages)
        messages.append({"role": "assistant", "content": reply})
        parsed = _parse_reply(reply)
        if parsed is None:
            _observe(messages, trace, PARSE_OBSERVATION)
            continue

        _record(trace, {"kind": "thought", "text": parsed["thought"]})
        if "draft" in parsed:
            if _draft_can_finish(status, ticket_filed, bound_item):
                _record(trace, {"kind": "draft", "text": parsed["draft"]})
                verdict, reply = _reflect(adapter, trace, parsed["draft"], status)
                print(f"Verdict: {verdict}", flush=True)
                print(f"Reply: {reply}", flush=True)
                return _finish(
                    employee_id,
                    query,
                    trace,
                    parsed["draft"],
                    "draft",
                    run_dir,
                    verdict=verdict,
                    reply=reply,
                )
            observation = (
                NEED_REVIEW_OBSERVATION
                if status in REVIEW_STATUSES or bound_item is None
                else NEED_STATUS_OBSERVATION
            )
            _observe(messages, trace, observation)
            continue

        tool = parsed["tool"]
        arguments = parsed["arguments"]
        _record(trace, {"kind": "action", "tool": tool, "arguments": arguments})
        if tool == FLAG_TOOL and not _flag_allowed(status, bound_item):
            _observe(messages, trace, _flag_blocked_observation(status))
            continue
        if _employee_arg(arguments) not in (None, employee_id):
            _observe(messages, trace, EMPLOYEE_LOCKED_OBSERVATION)
            continue
        if tool == ELIGIBILITY_TOOL and bound_item is None:
            _observe(messages, trace, NO_ITEM_ELIGIBILITY_OBSERVATION)
            continue
        if bound_item is not None and _item_arg(arguments) not in (None, bound_item):
            _observe(messages, trace, ITEM_LOCKED_OBSERVATION)
            continue
        if tool == ELIGIBILITY_TOOL and not looked_up:
            _observe(messages, trace, NEED_LOOKUP_OBSERVATION)
            continue
        if tool == ELIGIBILITY_TOOL and employee_found and not policy_ok:
            _observe(messages, trace, NEED_POLICY_OBSERVATION)
            continue

        result = await client.call_tool(tool, arguments)
        _observe(messages, trace, result["text"])
        if result["is_error"]:
            continue
        if tool == LOOKUP_TOOL:
            found, role = _lookup_result(result["text"])
            if found is not None:
                looked_up = True
                employee_found = found
                record_role = role
        elif tool == POLICY_TOOL:
            if (
                employee_found
                and record_role is not None
                and _role_arg(arguments) == record_role
            ):
                policy_ok = True
        elif tool == ELIGIBILITY_TOOL:
            found = _status_from_eligibility(result["text"])
            if found is not None:
                status = found
        elif tool == FLAG_TOOL:
            ticket_filed = True

    print(f"Reply: {STEP_LIMIT_REPLY}", flush=True)
    return _finish(
        employee_id,
        query,
        trace,
        None,
        "step_limit",
        run_dir,
        reply=STEP_LIMIT_REPLY,
    )


def _bound_item(adapter: ModelAdapter, employee_id: str, query: str) -> str | None:
    """One extract call. A single name is bound. Anything else leaves the item unset."""
    parsed = parse_extract(
        adapter.complete(
            [
                {"role": "system", "content": extract_prompt()},
                {
                    "role": "user",
                    "content": f"Employee id: {employee_id}\nQuery: {query}",
                },
            ]
        )
    )
    if parsed is None or "items" in parsed:
        return None
    return parsed["item"]


def _react_user(employee_id: str, query: str, bound_item: str | None) -> str:
    """The ReAct user message. The item is included only when extract bound one."""
    text = f"Employee id: {employee_id}\nQuery: {query}"
    if bound_item is not None:
        text += f"\nItem: {bound_item}"
    return text


def _item_arg(arguments: dict) -> str | None:
    """The normalized item argument, if the call named one."""
    return _normalized_arg(arguments, "item")


def _employee_arg(arguments: dict) -> str | None:
    """The employee id argument, if the call named one."""
    value = arguments.get("employee_id")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _role_arg(arguments: dict) -> str | None:
    """The normalized role argument, if the call named one."""
    return _normalized_arg(arguments, "role")


def _normalized_arg(arguments: dict, key: str) -> str | None:
    """Strip and lowercase one string argument."""
    value = arguments.get(key)
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    return text or None


def _lookup_result(text: str) -> tuple[bool | None, str | None]:
    """Whether the lookup found a person, and the role when it did."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(body, dict):
        return None, None
    if body.get("status") == "not_found":
        return False, None
    role = body.get("role")
    if not isinstance(role, str) or not role.strip():
        return None, None
    return True, role.strip().lower()


def _flag_allowed(status: str | None, bound_item: str | None) -> bool:
    """A ticket is allowed after a review status, or when no single item was bound."""
    if status in REVIEW_STATUSES:
        return True
    return status is None and bound_item is None


def _draft_can_finish(
    status: str | None, ticket_filed: bool, bound_item: str | None
) -> bool:
    """A clear status can end on a draft. A review path can end after a ticket."""
    if status in DECISIVE_STATUSES:
        return True
    if status in REVIEW_STATUSES and ticket_filed:
        return True
    return status is None and bound_item is None and ticket_filed


def _record(trace: list[dict], event: dict) -> None:
    """Store one trace event and print it."""
    trace.append(event)
    print(format_event(event), flush=True)


def _observe(messages: list[dict], trace: list[dict], text: str) -> None:
    """Append one observation to the transcript and the trace."""
    _record(trace, {"kind": "observation", "text": text})
    messages.append({"role": "user", "content": f"Observation: {text}"})


def _reflect(
    adapter: ModelAdapter,
    trace: list[dict],
    draft: str,
    status: str | None,
) -> tuple[str, str]:
    """Check the draft against observations. A bad reply falls back to the tool reason."""
    observations = [
        event["text"] for event in trace if event["kind"] == "observation"
    ]
    reflected = reflect(adapter, observations, draft)
    return employee_reply(status, _eligibility_reason(trace), reflected, draft)


def _eligibility_reason(trace: list[dict]) -> str | None:
    """The reason from the latest classification observation."""
    reason = None
    for event in trace:
        if event["kind"] != "observation":
            continue
        try:
            body = json.loads(event["text"])
        except json.JSONDecodeError:
            continue
        if isinstance(body, dict) and isinstance(body.get("reason"), str):
            if body.get("status") in DECISIVE_STATUSES or body.get("status") in REVIEW_STATUSES:
                reason = body["reason"]
    return reason


def _finish(
    employee_id: str,
    query: str,
    trace: list[dict],
    draft: str | None,
    stop: str,
    run_dir: Path | None,
    *,
    verdict: str | None = None,
    reply: str | None = None,
) -> dict:
    """Write the printed trace to one file and return the run."""
    path = None
    if run_dir is not None:
        path = run_path(run_dir, employee_id, query)
        write_run(path, format_run(trace, verdict=verdict, reply=reply))
    return {
        "trace": trace,
        "draft": draft,
        "stop": stop,
        "verdict": verdict,
        "reply": reply,
        "run_path": None if path is None else str(path),
    }

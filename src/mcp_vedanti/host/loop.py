"""ReAct loop for one equipment request.

One model call per step. The transcript grows with each thought, action, and observation.
"""

import json
from pathlib import Path
from typing import Protocol

from mcp_vedanti.host.adapter import ModelAdapter
from mcp_vedanti.host.client import EquipmentClient
from mcp_vedanti.host.prompt import agent_prompt
from mcp_vedanti.host.runlog import RUNS_DIR, format_event, format_run, run_path, write_run


class ToolCaller(Protocol):
    """The two host client calls the loop uses."""

    async def list_tools(self) -> list[dict]:
        """Return the tool catalog."""

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Return text and is_error for one tool call."""

STEP_LIMIT = 8
ELIGIBILITY_TOOL = "check_request_eligibility"
FLAG_TOOL = "flag_for_human_review"
DECISIVE_STATUSES = {"in_policy", "out_of_policy"}
REVIEW_STATUSES = {"indeterminate", "not_found"}

PARSE_OBSERVATION = (
    "The reply was not one JSON object with a thought and either a tool "
    "or a draft."
)
NEED_REVIEW_OBSERVATION = "A review has to be filed before a reply."
NEED_STATUS_OBSERVATION = (
    "Classification has not returned, so a draft cannot finish the request."
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
) -> dict:
    """Run one request. Prints the trace and writes the same text to one file."""
    if client is None:
        async with EquipmentClient() as connected:
            return await _run(
                employee_id, query, adapter, connected, step_limit, run_dir
            )
    return await _run(employee_id, query, adapter, client, step_limit, run_dir)


async def _run(
    employee_id: str,
    query: str,
    adapter: ModelAdapter,
    client: ToolCaller,
    step_limit: int,
    run_dir: Path | None,
) -> dict:
    tools = await client.list_tools()
    messages = [
        {"role": "system", "content": agent_prompt(tools)},
        {
            "role": "user",
            "content": f"Employee id: {employee_id}\nQuery: {query}",
        },
    ]
    trace: list[dict] = []
    status: str | None = None
    ticket_filed = False

    for _ in range(step_limit):
        reply = adapter.complete(messages)
        messages.append({"role": "assistant", "content": reply})
        parsed = _parse_reply(reply)
        if parsed is None:
            _observe(messages, trace, PARSE_OBSERVATION)
            continue

        _record(trace, {"kind": "thought", "text": parsed["thought"]})
        if "draft" in parsed:
            if _draft_can_finish(status, ticket_filed):
                _record(trace, {"kind": "draft", "text": parsed["draft"]})
                return _finish(employee_id, query, trace, parsed["draft"], "draft", run_dir)
            observation = (
                NEED_REVIEW_OBSERVATION
                if status in REVIEW_STATUSES
                else NEED_STATUS_OBSERVATION
            )
            _observe(messages, trace, observation)
            continue

        tool = parsed["tool"]
        arguments = parsed["arguments"]
        _record(trace, {"kind": "action", "tool": tool, "arguments": arguments})
        if tool == FLAG_TOOL and status not in REVIEW_STATUSES:
            _observe(messages, trace, _flag_blocked_observation(status))
            continue

        result = await client.call_tool(tool, arguments)
        _observe(messages, trace, result["text"])
        if result["is_error"]:
            continue
        if tool == ELIGIBILITY_TOOL:
            found = _status_from_eligibility(result["text"])
            if found is not None:
                status = found
        elif tool == FLAG_TOOL:
            ticket_filed = True

    return _finish(employee_id, query, trace, None, "step_limit", run_dir)


def _draft_can_finish(status: str | None, ticket_filed: bool) -> bool:
    """A clear status can end on a draft. A review status can end after a ticket."""
    if status in DECISIVE_STATUSES:
        return True
    return status in REVIEW_STATUSES and ticket_filed


def _record(trace: list[dict], event: dict) -> None:
    """Store one trace event and print it."""
    trace.append(event)
    print(format_event(event), flush=True)


def _observe(messages: list[dict], trace: list[dict], text: str) -> None:
    """Append one observation to the transcript and the trace."""
    _record(trace, {"kind": "observation", "text": text})
    messages.append({"role": "user", "content": f"Observation: {text}"})


def _finish(
    employee_id: str,
    query: str,
    trace: list[dict],
    draft: str | None,
    stop: str,
    run_dir: Path | None,
) -> dict:
    """Write the printed trace to one file and return the run."""
    path = None
    if run_dir is not None:
        path = run_path(run_dir, employee_id, query)
        write_run(path, format_run(trace))
    return {
        "trace": trace,
        "draft": draft,
        "stop": stop,
        "run_path": None if path is None else str(path),
    }

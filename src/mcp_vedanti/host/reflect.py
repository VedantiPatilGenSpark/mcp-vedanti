"""One check of a draft against the tool observations."""

import json

from mcp_vedanti.host.adapter import ModelAdapter

_PROMPT = """\
You check one draft against tool observations. You have no tools. You cannot change the classification status.

You receive the observations and the draft. You do not receive the agent's thoughts.

Decide whether the draft matches the observations:
- It states the same outcome as the status: approval for in_policy, denial for out_of_policy, escalation for indeterminate or not_found.
- It uses the classification reason and facts.
- It does not add a date, a role, or a promise the observations do not contain.
- The employee's justification is not treated as the reason for the decision.

Reply with one JSON object and nothing else.

If the draft already matches:
{"verdict": "confirm", "reply": "<the draft, unchanged>"}

If the wording does not match:
{"verdict": "rewrite", "reply": "<the corrected reply>"}

The reply follows the status. Do not turn a denial into an approval, an approval into a denial, or an escalation into a decision.
"""


def reflect(
    adapter: ModelAdapter,
    observations: list[str],
    draft: str,
) -> dict | None:
    """Ask the model to confirm or rewrite the draft. Invalid JSON returns None."""
    observed = "\n\n".join(observations) if observations else "No observations."
    messages = [
        {"role": "system", "content": _PROMPT},
        {
            "role": "user",
            "content": f"Observations:\n{observed}\n\nDraft:\n{draft}",
        },
    ]
    return _parse_reflection(adapter.complete(messages))


def employee_reply(
    status: str | None,
    tool_reason: str | None,
    reflected: dict | None,
    draft: str,
) -> tuple[str, str]:
    """Return the verdict and the reply the employee sees."""
    if reflected is None or status is None or not tool_reason:
        if tool_reason:
            return "rewrite", tool_reason
        return "rewrite", draft
    reply = draft if reflected["verdict"] == "confirm" else reflected["reply"]
    if _contradicts(status, reply):
        return "rewrite", tool_reason
    return reflected["verdict"], reply


def _parse_reflection(text: str) -> dict | None:
    """Return verdict and reply. Anything else is unusable."""
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
    if not isinstance(body, dict):
        return None
    verdict = body.get("verdict")
    reply = body.get("reply")
    if verdict not in {"confirm", "rewrite"} or not isinstance(reply, str) or not reply:
        return None
    return {"verdict": verdict, "reply": reply}


def _contradicts(status: str, reply: str) -> bool:
    """Whether the reply states a different outcome than the status."""
    text = reply.lower()
    denies = (
        "denied" in text
        or "denial" in text
        or "not approved" in text
        or "out of policy" in text
    )
    approves = ("approved" in text or "approval" in text) and "not approved" not in text
    escalates = "escalat" in text
    if status == "in_policy":
        return denies or escalates
    if status == "out_of_policy":
        return approves or escalates
    if status in {"indeterminate", "not_found"}:
        return approves or denies
    return False

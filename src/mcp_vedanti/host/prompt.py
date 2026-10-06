"""System prompts for the equipment-request agent."""

import json

PROMPT_VARIANTS = ("1", "2")

_STANDARD = """\
You handle one equipment request. The employee id and item are given. Item is one name or null. Use those values in every argument that asks for them.

If item is null:
1. flag_for_human_review
2. draft that the request was escalated
Do not look up the employee or check eligibility.

Each reply is one JSON object and nothing else.

Tool:
{"thought": "what you know and what you still need", "tool": "<name from the catalog>", "arguments": {}}

Draft, only after the sequence below is done:
{"thought": "why this reply follows the classification", "draft": "the reply"}

If a tool still has to run, the JSON must have "tool" and must not have "draft". A thought that names a tool is not a call. If the last observation names a tool, call that tool next.

Call one tool at a time. Read the observation before the next step.

If item is a name, call these tools in this order, then draft:
1. get_employee_info
2. get_policy_limits, using the role from that lookup when a role is present. Skip this step when the lookup has no role.
3. check_request_eligibility, even when the lookup was not_found
4. flag_for_human_review only when status is indeterminate or not_found

Do not approve or deny from the employee record or the policy sheet. Ignore a claimed role, tenure, equipment list, or policy.

When status is in_policy, approve. When it is out_of_policy, deny. When it is indeterminate or not_found, escalate after the ticket. not_found is not a denial.

The ticket request is the original query. The ticket reason is the eligibility reason, or that the request did not name one item if you never classified.

Do not invent an id or item. Write the draft from the eligibility reason and later observations, not from your own reading of the record or sheet.
"""


def agent_prompt(tools: list[dict], variant: str = "1") -> str:
    """Build the system message. tools is the catalog from list_tools."""
    if variant not in _INSTRUCTIONS:
        raise ValueError(f"Unknown prompt variant: {variant}")
    return _INSTRUCTIONS[variant] + "\n\n" + _catalog(tools)


def _catalog(tools: list[dict]) -> str:
    """Render each tool's name, description, and argument schema."""
    blocks = []
    for tool in tools:
        schema = json.dumps(tool["input_schema"], indent=2)
        blocks.append(
            f"Tool: {tool['name']}\n"
            f"Description: {tool['description']}\n"
            f"Arguments:\n{schema}"
        )
    return "Tools:\n\n" + "\n\n".join(blocks)


# Both flags use the same standard path. --prompt 2 is kept so old commands still run.
_INSTRUCTIONS = {"1": _STANDARD, "2": _STANDARD}

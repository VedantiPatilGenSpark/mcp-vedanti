"""Confirm the host loop with a scripted model. No Ollama server is used."""

import asyncio
import json

from mcp_vedanti.host.extract import extract_prompt
from mcp_vedanti.host.loop import STEP_LIMIT_REPLY, run_request


CATALOG = [
    {
        "name": "get_employee_info",
        "description": "Look up one employee.",
        "input_schema": {},
    },
    {
        "name": "get_policy_limits",
        "description": "Read one role sheet.",
        "input_schema": {},
    },
    {
        "name": "check_request_eligibility",
        "description": "Classify one employee and item.",
        "input_schema": {},
    },
    {
        "name": "flag_for_human_review",
        "description": "Append one escalation ticket.",
        "input_schema": {},
    },
]


class ScriptedModel:
    """Return queued replies and keep each transcript it was shown."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.transcripts: list[list[dict]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.transcripts.append(messages)
        return self._replies.pop(0)


class ScriptedTools:
    """Return queued tool results and record each call."""

    def __init__(self, results: list[dict]) -> None:
        self._results = list(results)
        self.calls: list[str] = []

    async def list_tools(self) -> list[dict]:
        return CATALOG

    async def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append(name)
        return self._results.pop(0)


def _tool(name: str, **arguments: str) -> str:
    return json.dumps({"thought": f"Call {name}.", "tool": name, "arguments": arguments})


def _draft(text: str) -> str:
    return json.dumps({"thought": "The reply is ready.", "draft": text})


def _reflection(verdict: str, reply: str) -> str:
    return json.dumps({"verdict": verdict, "reply": reply})


def _eligibility(status: str, reason: str) -> dict:
    return {
        "text": json.dumps({"status": status, "reason": reason, "facts": {}}),
        "is_error": False,
    }


def _employee_found(employee_id: str = "E201", role: str = "manager") -> dict:
    return {
        "text": json.dumps(
            {
                "employee_id": employee_id,
                "role": role,
                "tenure_years": 7.3,
                "equipment": [],
            }
        ),
        "is_error": False,
    }


def _employee_missing(employee_id: str = "E999") -> dict:
    return {
        "text": json.dumps({"employee_id": employee_id, "status": "not_found"}),
        "is_error": False,
    }


def _policy(role: str = "manager") -> dict:
    return {"text": json.dumps({"role": role, "items": []}), "is_error": False}


def _ticket() -> dict:
    return {"text": json.dumps({"escalation_id": "ESC-1"}), "is_error": False}


def _extract(*, item: str | None = None, items: list[str] | None = None) -> str:
    body: dict = {"thought": "Name the item."}
    if items is not None:
        body["items"] = items
    else:
        body["item"] = item
    return json.dumps(body)


def _run(
    model: ScriptedModel,
    tools: ScriptedTools,
    employee_id: str = "E201",
    query: str = "I need a second monitor.",
) -> dict:
    return asyncio.run(
        run_request(
            employee_id,
            query,
            model,
            client=tools,
            run_dir=None,
        )
    )


def test_tool_step_records_thought_action_and_observation() -> None:
    """One tool call lands in the trace as thought, action, then observation."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
    ]
    eligibility = [
        event
        for event in result["trace"]
        if event["kind"] == "action" and event["tool"] == "check_request_eligibility"
    ]
    assert eligibility
    assert any(
        event["kind"] == "observation" and "under the limit" in event["text"]
        for event in result["trace"]
    )


def test_rejected_argument_is_an_observation() -> None:
    """A rejected tool call is an observation, and the model gets another step."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            {"text": "employee_id must be a string", "is_error": True},
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
        "check_request_eligibility",
    ]
    assert any(
        event["kind"] == "observation" and event["text"] == "employee_id must be a string"
        for event in result["trace"]
    )
    assert result["reply"] == "Your second monitor is approved."


def test_flag_is_blocked_when_status_is_in_policy() -> None:
    """A ticket call does not reach the server after an in-policy classification."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _tool("flag_for_human_review", employee_id="E201", request="x", reason="y"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
    ]
    assert any(
        event["kind"] == "observation" and "does not allow a ticket" in event["text"]
        for event in result["trace"]
    )


def test_draft_is_held_until_a_ticket_exists() -> None:
    """An indeterminate draft does not finish the loop before the review is filed."""
    model = ScriptedModel(
        [
            _extract(item="headset"),
            _tool("get_employee_info", employee_id="E207"),
            _tool("get_policy_limits", role="standard"),
            _tool("check_request_eligibility", employee_id="E207", item="headset"),
            _draft("Approved."),
            _tool(
                "flag_for_human_review",
                employee_id="E207",
                request="I need a headset.",
                reason="Item 'headset' is not in the catalog.",
            ),
            _draft("The request was escalated."),
            _reflection("confirm", "The request was escalated."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found("E207", "standard"),
            _policy("standard"),
            _eligibility("indeterminate", "Item 'headset' is not in the catalog."),
            _ticket(),
        ]
    )

    result = _run(model, tools, employee_id="E207", query="I need a headset.")

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
        "flag_for_human_review",
    ]
    assert any(
        event["kind"] == "observation" and "review has to be filed" in event["text"]
        for event in result["trace"]
    )
    assert result["draft"] == "The request was escalated."
    assert result["reply"] == "The request was escalated."


def test_reflector_runs_on_observations_before_the_reply() -> None:
    """The reflector sees the observations and the draft, and the reply comes after it."""
    draft = "Your second monitor is approved."
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft(draft),
            _reflection("confirm", "This text is ignored on confirm."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    reflector = model.transcripts[-1]
    assert reflector[0]["content"].startswith("You check one draft")
    user_message = reflector[1]["content"]
    assert "Count is under the limit." in user_message
    assert draft in user_message
    assert "Call check_request_eligibility." not in user_message
    assert result["verdict"] == "confirm"
    assert result["reply"] == draft


def test_contradicting_reply_falls_back_to_the_tool_reason() -> None:
    """A reply that denies an in-policy result is replaced by the tool reason."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is denied."),
            _reflection("confirm", "Your second monitor is denied."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert result["verdict"] == "rewrite"
    assert result["reply"] == "Count is under the limit."


def test_extract_runs_before_react() -> None:
    """The first model call is extract. ReAct then sees the bound item."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert model.transcripts[0][0]["content"] == extract_prompt()
    react_user = model.transcripts[1][1]["content"]
    assert "Item: monitor" in react_user
    assert result["reply"] == "Your second monitor is approved."


def test_tool_item_must_match_extract() -> None:
    """A tool argument that changes the bound item does not reach the server."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="laptop"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
    ]
    assert any(
        event["kind"] == "observation" and "item" in event["text"].lower()
        for event in result["trace"]
    )


def test_missing_item_allows_flag_without_eligibility() -> None:
    """A query with no item files a review and never classifies."""
    model = ScriptedModel(
        [
            _extract(item=None),
            _tool(
                "flag_for_human_review",
                employee_id="E203",
                request="I know it's early, please approve it anyway.",
                reason="The request does not name an item.",
            ),
            _draft("The request was escalated."),
            _reflection("confirm", "The request was escalated."),
        ]
    )
    tools = ScriptedTools(
        [{"text": json.dumps({"escalation_id": "ESC-1"}), "is_error": False}]
    )

    result = _run(
        model,
        tools,
        employee_id="E203",
        query="I know it's early, please approve it anyway.",
    )

    assert tools.calls == ["flag_for_human_review"]
    assert result["reply"] == "The request was escalated."


def test_two_items_allows_flag_without_eligibility() -> None:
    """Two named items file a review and never classify."""
    model = ScriptedModel(
        [
            _extract(items=["monitor", "laptop"]),
            _tool(
                "flag_for_human_review",
                employee_id="E201",
                request="I want a monitor and a laptop.",
                reason="The request named more than one item.",
            ),
            _draft("The request was escalated."),
            _reflection("confirm", "The request was escalated."),
        ]
    )
    tools = ScriptedTools(
        [{"text": json.dumps({"escalation_id": "ESC-1"}), "is_error": False}]
    )

    result = _run(
        model,
        tools,
        employee_id="E201",
        query="I want a monitor and a laptop.",
    )

    assert tools.calls == ["flag_for_human_review"]
    assert result["reply"] == "The request was escalated."


def test_unusable_extract_is_treated_as_no_item() -> None:
    """A bad extract reply takes the missing-item path instead of entering ReAct parse errors."""
    model = ScriptedModel(
        [
            "not json",
            _tool(
                "flag_for_human_review",
                employee_id="E201",
                request="I need a second monitor.",
                reason="The request does not name an item.",
            ),
            _draft("The request was escalated."),
            _reflection("confirm", "The request was escalated."),
        ]
    )
    tools = ScriptedTools(
        [{"text": json.dumps({"escalation_id": "ESC-1"}), "is_error": False}]
    )

    result = _run(model, tools)

    assert tools.calls == ["flag_for_human_review"]
    assert result["reply"] == "The request was escalated."


def test_eligibility_is_blocked_before_employee_lookup() -> None:
    """Eligibility does not reach the server until the employee has been looked up."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
    ]
    assert any(
        event["kind"] == "observation" and "employee" in event["text"].lower()
        for event in result["trace"]
    )


def test_eligibility_is_blocked_before_policy_when_found() -> None:
    """A found employee still needs the role sheet before eligibility."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
    ]
    assert any(
        event["kind"] == "observation" and "policy" in event["text"].lower()
        for event in result["trace"]
    )


def test_policy_must_use_the_record_role() -> None:
    """A sheet for the wrong role does not unlock eligibility."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="standard"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy("standard"),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "get_policy_limits",
        "check_request_eligibility",
    ]
    assert result["reply"] == "Your second monitor is approved."


def test_missing_employee_skips_policy_and_still_classifies() -> None:
    """A not-found lookup does not need a sheet. Eligibility then a ticket."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E999"),
            _tool("check_request_eligibility", employee_id="E999", item="monitor"),
            _tool(
                "flag_for_human_review",
                employee_id="E999",
                request="I need a monitor.",
                reason="No employee E999 is on file.",
            ),
            _draft("The request was escalated."),
            _reflection("confirm", "The request was escalated."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_missing(),
            _eligibility("not_found", "No employee E999 is on file."),
            _ticket(),
        ]
    )

    result = _run(model, tools, employee_id="E999", query="I need a monitor.")

    assert tools.calls == [
        "get_employee_info",
        "check_request_eligibility",
        "flag_for_human_review",
    ]
    assert result["reply"] == "The request was escalated."


def test_tool_employee_id_must_match() -> None:
    """A tool argument that changes the employee id does not reach the server."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            _tool("get_employee_info", employee_id="E999"),
            _tool("get_employee_info", employee_id="E201"),
            _tool("get_policy_limits", role="manager"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            _employee_found(),
            _policy(),
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
    ]
    assert any(
        event["kind"] == "observation" and "employee" in event["text"].lower()
        for event in result["trace"]
    )
    assert result["reply"] == "Your second monitor is approved."


def test_step_limit_prints_an_employee_reply() -> None:
    """A run that never drafts still leaves the employee a reply."""
    model = ScriptedModel(
        [
            _extract(item="monitor"),
            "not json",
            "not json",
        ]
    )
    tools = ScriptedTools([])

    result = asyncio.run(
        run_request(
            "E201",
            "I need a second monitor.",
            model,
            client=tools,
            step_limit=2,
            run_dir=None,
        )
    )

    assert result["stop"] == "step_limit"
    assert result["reply"] == STEP_LIMIT_REPLY
    assert result["draft"] is None

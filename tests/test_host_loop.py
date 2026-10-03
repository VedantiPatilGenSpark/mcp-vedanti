"""Confirm the host loop with a scripted model. No Ollama server is used."""

import asyncio
import json

from mcp_vedanti.host.loop import run_request


CATALOG = [
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


def _run(model: ScriptedModel, tools: ScriptedTools) -> dict:
    return asyncio.run(
        run_request(
            "E201",
            "I need a second monitor.",
            model,
            client=tools,
            run_dir=None,
        )
    )


def test_tool_step_records_thought_action_and_observation() -> None:
    """One tool call lands in the trace as thought, action, then observation."""
    model = ScriptedModel(
        [
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools([_eligibility("in_policy", "Count is under the limit.")])

    result = _run(model, tools)

    assert tools.calls == ["check_request_eligibility"]
    assert [event["kind"] for event in result["trace"][:3]] == [
        "thought",
        "action",
        "observation",
    ]
    assert result["trace"][1]["tool"] == "check_request_eligibility"
    assert "under the limit" in result["trace"][2]["text"]


def test_rejected_argument_is_an_observation() -> None:
    """A rejected tool call is an observation, and the model gets another step."""
    model = ScriptedModel(
        [
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools(
        [
            {"text": "employee_id must be a string", "is_error": True},
            _eligibility("in_policy", "Count is under the limit."),
        ]
    )

    result = _run(model, tools)

    assert tools.calls == ["check_request_eligibility", "check_request_eligibility"]
    assert result["trace"][2]["text"] == "employee_id must be a string"
    assert result["reply"] == "Your second monitor is approved."


def test_flag_is_blocked_when_status_is_in_policy() -> None:
    """A ticket call does not reach the server after an in-policy classification."""
    model = ScriptedModel(
        [
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _tool("flag_for_human_review", employee_id="E201", request="x", reason="y"),
            _draft("Your second monitor is approved."),
            _reflection("confirm", "Your second monitor is approved."),
        ]
    )
    tools = ScriptedTools([_eligibility("in_policy", "Count is under the limit.")])

    result = _run(model, tools)

    assert tools.calls == ["check_request_eligibility"]
    assert any(
        event["kind"] == "observation" and "does not allow a ticket" in event["text"]
        for event in result["trace"]
    )


def test_draft_is_held_until_a_ticket_exists() -> None:
    """An indeterminate draft does not finish the loop before the review is filed."""
    model = ScriptedModel(
        [
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
            _eligibility("indeterminate", "Item 'headset' is not in the catalog."),
            {
                "text": json.dumps({"escalation_id": "ESC-1"}),
                "is_error": False,
            },
        ]
    )

    result = _run(model, tools)

    assert tools.calls == ["check_request_eligibility", "flag_for_human_review"]
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
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft(draft),
            _reflection("confirm", "This text is ignored on confirm."),
        ]
    )
    tools = ScriptedTools([_eligibility("in_policy", "Count is under the limit.")])

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
            _tool("check_request_eligibility", employee_id="E201", item="monitor"),
            _draft("Your second monitor is denied."),
            _reflection("confirm", "Your second monitor is denied."),
        ]
    )
    tools = ScriptedTools([_eligibility("in_policy", "Count is under the limit.")])

    result = _run(model, tools)

    assert result["verdict"] == "rewrite"
    assert result["reply"] == "Count is under the limit."

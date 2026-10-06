"""Confirm the ReAct system prompt keeps outcome rules and drops extract/order essays."""

from mcp_vedanti.host.prompt import agent_prompt


def _prompt() -> str:
    return agent_prompt(
        [
            {
                "name": "get_employee_info",
                "description": "Look up one employee.",
                "input_schema": {},
            }
        ]
    )


def test_prompt_includes_the_tool_catalog() -> None:
    """Live tool names from list_tools stay in the system message."""
    assert "get_employee_info" in _prompt()
    assert "Look up one employee." in _prompt()


def test_prompt_keeps_react_json_and_status_rules() -> None:
    """The model still chooses a tool or a draft and follows eligibility status."""
    text = _prompt()
    assert '"tool"' in text
    assert '"draft"' in text
    assert "in_policy" in text
    assert "out_of_policy" in text
    assert "indeterminate" in text
    assert "not_found" in text


def test_prompt_ignores_claimed_role_and_tenure() -> None:
    """Claimed facts in the query still do not override the record."""
    lowered = _prompt().lower()
    assert "role" in lowered
    assert "tenure" in lowered


def test_prompt_does_not_ask_the_model_to_extract_the_item() -> None:
    """Item extract is a prelude. ReAct must not re-do it."""
    lowered = _prompt().lower()
    assert "equipment word" not in lowered
    assert "computer is not a laptop" not in lowered


def test_prompt_does_not_forbid_a_ticket_before_eligibility() -> None:
    """No-item and two-item paths file a review with no classification status."""
    lowered = _prompt().lower()
    assert "do not file a review, until that check" not in lowered
    assert "do not draft, and do not file a review" not in lowered

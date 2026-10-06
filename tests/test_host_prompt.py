"""Confirm the ReAct system prompt keeps outcome rules and drops extract/order essays."""

from mcp_vedanti.host.prompt import _PROMPT, agent_prompt
from mcp_vedanti.host.reflect import _PROMPT as _REFLECT


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


def test_prompt_names_jobs_in_plain_english() -> None:
    """Instructions describe jobs. Exact tool names come from the catalog only."""
    assert "get the employee info" in _PROMPT
    assert "get the policy limits" in _PROMPT
    assert "check the request eligibility" in _PROMPT
    assert "flag for human review" in _PROMPT
    assert "get_employee_info" not in _PROMPT
    assert "get_policy_limits" not in _PROMPT
    assert "check_request_eligibility" not in _PROMPT
    assert "flag_for_human_review" not in _PROMPT


def test_prompt_routes_a_null_item_to_flag() -> None:
    """ReAct always sees an item field. Null means flag, then draft."""
    text = _PROMPT.lower()
    assert "item is null" in text
    assert "flag for human review" in text


def test_prompt_requires_a_tool_object_until_the_sequence_is_done() -> None:
    """Blocked drafts come from emitting draft while a tool is still due."""
    assert 'must have "tool"' in _PROMPT
    assert 'must not have "draft"' in _PROMPT
    assert "even when the employee was not found" in _PROMPT
    assert "Never draft after employee info or policy limits alone." in _PROMPT


def test_prompt_asks_for_an_employee_facing_reply() -> None:
    """Approve, deny, and escalate are written to the employee, not as a case note."""
    text = _PROMPT.lower()
    assert "second person" in text
    assert "can have the item" in text
    assert "cannot fulfill this request" in text
    assert "a person will review this request" in text
    assert "ticket ids" in text


def test_reflector_asks_for_an_employee_facing_reply() -> None:
    """The wording check keeps you/your and drops status codes and ticket ids."""
    text = _REFLECT.lower()
    assert "you/your" in text
    assert "ticket ids" in text

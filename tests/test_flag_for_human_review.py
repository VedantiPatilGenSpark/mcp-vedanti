"""Confirm the escalation store appends a ticket and can be cleared."""

import mcp_vedanti.equipment as equipment
from mcp_vedanti.data import EMPLOYEES
from mcp_vedanti.equipment import flag_for_human_review, reset_escalations


def test_one_call_stores_and_returns_the_record() -> None:
    """One call stores ESC-1 and returns a copy of that same ticket."""
    reset_escalations()

    returned = flag_for_human_review(
        "E201",
        "I need a second monitor.",
        "Refresh is inside the early-request buffer.",
    )

    expected = {
        "escalation_id": "ESC-1",
        "employee_id": "E201",
        "request": "I need a second monitor.",
        "reason": "Refresh is inside the early-request buffer.",
    }
    assert returned == expected
    assert equipment.escalations == [expected]
    assert returned is not equipment.escalations[0]


def test_second_call_appends_esc_2() -> None:
    """A second call returns ESC-2, and the store holds both tickets in order."""
    reset_escalations()

    flag_for_human_review("E201", "First request.", "First reason.")
    second = flag_for_human_review("E204", "Second request.", "Second reason.")

    assert second["escalation_id"] == "ESC-2"
    assert equipment.escalations == [
        {
            "escalation_id": "ESC-1",
            "employee_id": "E201",
            "request": "First request.",
            "reason": "First reason.",
        },
        {
            "escalation_id": "ESC-2",
            "employee_id": "E204",
            "request": "Second request.",
            "reason": "Second reason.",
        },
    ]


def test_reset_escalations_restarts_at_esc_1() -> None:
    """After a reset, the next stored ticket is ESC-1 again."""
    reset_escalations()
    flag_for_human_review("E201", "First request.", "First reason.")
    flag_for_human_review("E204", "Second request.", "Second reason.")

    reset_escalations()
    returned = flag_for_human_review("E203", "After reset.", "Start again.")

    assert returned["escalation_id"] == "ESC-1"
    assert equipment.escalations == [
        {
            "escalation_id": "ESC-1",
            "employee_id": "E203",
            "request": "After reset.",
            "reason": "Start again.",
        }
    ]


def test_unknown_employee_is_stored() -> None:
    """An unknown employee id is still stored and does not return not-found."""
    reset_escalations()

    returned = flag_for_human_review("E999", "I need a monitor.", "No employee E999")

    expected = {
        "escalation_id": "ESC-1",
        "employee_id": "E999",
        "request": "I need a monitor.",
        "reason": "No employee E999",
    }
    assert returned == expected
    assert "status" not in returned
    assert equipment.escalations == [expected]


def test_flag_does_not_change_e202_equipment() -> None:
    """Filing a ticket does not change E202's equipment list in the data module."""
    reset_escalations()
    equipment_list = EMPLOYEES["E202"]["equipment"]

    flag_for_human_review("E202", "I need a laptop.", "Issue date is missing.")

    assert EMPLOYEES["E202"]["equipment"] is equipment_list
    assert equipment_list == [{"item": "monitor", "issued_on": "2023-08-01"}]

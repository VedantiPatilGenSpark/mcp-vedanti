"""Confirm check_request_eligibility classifies each employee and item case."""

import re

from mcp_vedanti.data import EMPLOYEES
from mcp_vedanti.equipment import check_request_eligibility


E201_MONITOR_FACTS = {
    "role": "manager",
    "tenure_years": 7.3,
    "count_on_file": 1,
    "newest_issued_on": "2025-01-01",
    "max_count": 2,
    "refresh_years": 3,
    "min_tenure_years": 0,
}


def _expect(
    result,
    *,
    employee_id,
    item,
    status,
    within_policy,
    facts=None,
    fact_fields=None,
    reason_has=(),
    reason_numbers=(),
):
    assert result["employee_id"] == employee_id
    assert result["item"] == item
    assert result["status"] == status
    assert result["within_policy"] is within_policy
    assert isinstance(result["reason"], str)
    lowered = result["reason"].lower()
    for fragment in reason_has:
        assert fragment.lower() in lowered
    for number in reason_numbers:
        assert re.search(rf"\b{number}\b", result["reason"])
    if facts is not None:
        assert result["facts"] == facts
    if fact_fields is not None:
        for key, value in fact_fields.items():
            assert result["facts"][key] == value


def test_e201_monitor_under_cap_is_in_policy() -> None:
    """One monitor under the manager cap of 2 is in policy even though it is not due."""
    result = check_request_eligibility("E201", "monitor")

    _expect(
        result,
        employee_id="E201",
        item="monitor",
        status="in_policy",
        within_policy=True,
        facts=E201_MONITOR_FACTS,
        reason_numbers=(1, 2),
    )


def test_e201_monitor_item_is_normalized() -> None:
    """Whitespace and capitals on the item normalize to monitor and stay in policy."""
    result = check_request_eligibility("E201", " Monitor ")

    _expect(
        result,
        employee_id="E201",
        item="monitor",
        status="in_policy",
        within_policy=True,
        facts=E201_MONITOR_FACTS,
        reason_numbers=(1, 2),
    )


def test_e202_monitor_already_due_is_in_policy() -> None:
    """At the cap, a monitor issued 2023-08-01 is already due on a 3-year refresh."""
    result = check_request_eligibility("E202", "monitor")

    _expect(
        result,
        employee_id="E202",
        item="monitor",
        status="in_policy",
        within_policy=True,
        facts={
            "role": "standard",
            "tenure_years": 8.6,
            "count_on_file": 1,
            "newest_issued_on": "2023-08-01",
            "max_count": 1,
            "refresh_years": 3,
            "min_tenure_years": 0,
        },
        reason_has=("2023-08-01",),
        reason_numbers=(3,),
    )


def test_e203_monitor_outside_buffer_is_out_of_policy() -> None:
    """At the cap, a due date more than 90 days away is out of policy."""
    result = check_request_eligibility("E203", "monitor")

    _expect(
        result,
        employee_id="E203",
        item="monitor",
        status="out_of_policy",
        within_policy=False,
        facts={
            "role": "standard",
            "tenure_years": 8.6,
            "count_on_file": 1,
            "newest_issued_on": "2024-01-15",
            "max_count": 1,
            "refresh_years": 3,
            "min_tenure_years": 0,
        },
        reason_has=("90", "day"),
    )


def test_e204_dock_absent_from_standard_sheet_is_out_of_policy() -> None:
    """A catalog item missing from the standard sheet is out of policy."""
    result = check_request_eligibility("E204", "dock")

    _expect(
        result,
        employee_id="E204",
        item="dock",
        status="out_of_policy",
        within_policy=False,
        facts={
            "role": "standard",
            "tenure_years": 8.6,
            "count_on_file": 0,
            "newest_issued_on": None,
            "max_count": None,
            "refresh_years": None,
            "min_tenure_years": None,
        },
        reason_has=("dock", "standard", "sheet"),
    )


def test_e205_laptop_tenure_below_minimum_is_out_of_policy() -> None:
    """Tenure 0.5 is below the standard laptop minimum of 1 year."""
    result = check_request_eligibility("E205", "laptop")

    _expect(
        result,
        employee_id="E205",
        item="laptop",
        status="out_of_policy",
        within_policy=False,
        facts={
            "role": "standard",
            "tenure_years": 0.5,
            "count_on_file": 0,
            "newest_issued_on": None,
            "max_count": 1,
            "refresh_years": 4,
            "min_tenure_years": 1,
        },
        reason_has=("0.5",),
        reason_numbers=(1,),
    )


def test_e205_monitor_with_no_tenure_gate_is_in_policy() -> None:
    """The same new employee is in policy for a monitor, whose minimum tenure is 0."""
    result = check_request_eligibility("E205", "monitor")

    _expect(
        result,
        employee_id="E205",
        item="monitor",
        status="in_policy",
        within_policy=True,
        facts={
            "role": "standard",
            "tenure_years": 0.5,
            "count_on_file": 0,
            "newest_issued_on": None,
            "max_count": 1,
            "refresh_years": 3,
            "min_tenure_years": 0,
        },
        reason_numbers=(0,),
    )


def test_missing_issue_date_at_the_cap_is_indeterminate() -> None:
    """At the cap, a missing issue date is indeterminate. The corpus has no blank date, so this inserts one temporarily."""
    employee_id = "E900"
    EMPLOYEES[employee_id] = {
        "employee_id": employee_id,
        "role": "standard",
        "hire_date": "2018-03-01",
        "equipment": [{"item": "monitor", "issued_on": None}],
    }
    try:
        result = check_request_eligibility(employee_id, "monitor")
    finally:
        del EMPLOYEES[employee_id]

    _expect(
        result,
        employee_id=employee_id,
        item="monitor",
        status="indeterminate",
        within_policy=None,
        fact_fields={"count_on_file": 1, "newest_issued_on": None},
        reason_has=("date",),
    )


def test_e207_headset_under_cap_is_in_policy() -> None:
    """E207 has no headset on file. Headset is on the standard sheet, so this is under the cap."""
    result = check_request_eligibility("E207", "headset")

    _expect(
        result,
        employee_id="E207",
        item="headset",
        status="in_policy",
        within_policy=True,
        facts={
            "role": "standard",
            "tenure_years": 8.6,
            "count_on_file": 0,
            "newest_issued_on": None,
            "max_count": 1,
            "refresh_years": 3,
            "min_tenure_years": 0,
        },
        reason_numbers=(0, 1),
    )


def test_e207_keyboard_is_not_in_the_catalog() -> None:
    """An item outside the catalog is indeterminate, not a denial."""
    result = check_request_eligibility("E207", "keyboard")

    _expect(
        result,
        employee_id="E207",
        item="keyboard",
        status="indeterminate",
        within_policy=None,
        reason_has=("keyboard", "catalog"),
    )


def test_e208_count_over_max_is_indeterminate() -> None:
    """Two monitors already on file is over the standard cap of 1."""
    result = check_request_eligibility("E208", "monitor")

    _expect(
        result,
        employee_id="E208",
        item="monitor",
        status="indeterminate",
        within_policy=None,
        fact_fields={"count_on_file": 2, "max_count": 1},
        reason_numbers=(2, 1),
    )


def test_e209_contractor_has_no_policy_sheet() -> None:
    """A person on file whose role has no sheet is indeterminate."""
    result = check_request_eligibility("E209", "monitor")

    _expect(
        result,
        employee_id="E209",
        item="monitor",
        status="indeterminate",
        within_policy=None,
        fact_fields={"role": "contractor"},
        reason_has=("contractor", "policy"),
    )


def test_e210_due_date_inside_buffer_is_indeterminate() -> None:
    """At the cap, a due date inside the 90-day window is indeterminate."""
    result = check_request_eligibility("E210", "monitor")

    _expect(
        result,
        employee_id="E210",
        item="monitor",
        status="indeterminate",
        within_policy=None,
        reason_has=("90",),
    )


def test_e211_split_history_names_both_issue_dates() -> None:
    """Split history is indeterminate, and the reason names both issue dates."""
    result = check_request_eligibility("E211", "monitor")

    _expect(
        result,
        employee_id="E211",
        item="monitor",
        status="indeterminate",
        within_policy=None,
        reason_has=("2020-06-01", "2026-06-01"),
    )


def test_e999_monitor_is_not_found() -> None:
    """A missing employee is not-found, and the result has no role or tenure facts."""
    result = check_request_eligibility("E999", "monitor")

    _expect(
        result,
        employee_id="E999",
        item="monitor",
        status="not_found",
        within_policy=None,
        reason_has=("E999",),
    )
    facts = result.get("facts") or {}
    assert "role" not in facts
    assert "tenure_years" not in facts
    assert "count_on_file" not in facts


def test_e999_keyboard_is_not_found_before_unknown_item() -> None:
    """A missing employee is decided before the unknown item, so keyboard is still not-found."""
    result = check_request_eligibility("E999", "keyboard")

    _expect(
        result,
        employee_id="E999",
        item="keyboard",
        status="not_found",
        within_policy=None,
        reason_has=("E999",),
    )

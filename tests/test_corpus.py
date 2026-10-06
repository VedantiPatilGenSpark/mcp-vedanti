"""Confirm the mock data exports: dates, catalog, policy sheets, and employees."""

import datetime

import pytest

from mcp_vedanti.data import (
    AS_OF,
    CATALOG_ITEMS,
    EARLY_REQUEST_DAYS,
    EMPLOYEES,
    POLICY,
    POLICY_ROLES,
)


def test_as_of_and_early_request_days() -> None:
    """The clock is 2026-10-01 and the early-request window is 90 days."""
    assert AS_OF == datetime.date(2026, 10, 1)
    assert EARLY_REQUEST_DAYS == 90


def test_catalog_items() -> None:
    """The catalog is monitor, laptop, dock, and headset. Keyboard is absent."""
    assert CATALOG_ITEMS == ("monitor", "laptop", "dock", "headset")
    assert "keyboard" not in CATALOG_ITEMS


def test_policy_roles() -> None:
    """The policy roles are standard, manager, and director, and contractor is absent."""
    assert POLICY_ROLES == ("standard", "manager", "director")
    assert "contractor" not in POLICY_ROLES


def test_policy_sheets() -> None:
    """Each sheet matches its limits, and the standard sheet has no dock row."""
    assert list(POLICY) == ["standard", "manager", "director"]
    assert POLICY["standard"] == [
        {"item": "monitor", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 4, "min_tenure_years": 1},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ]
    assert all(row["item"] != "dock" for row in POLICY["standard"])
    assert POLICY["manager"] == [
        {"item": "monitor", "max_count": 2, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "dock", "max_count": 1, "refresh_years": 4, "min_tenure_years": 0},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ]
    assert POLICY["director"] == [
        {"item": "monitor", "max_count": 2, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "dock", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ]


def test_employee_ids() -> None:
    """The employee keys are exactly E201 through E205 and E207 through E212."""
    assert list(EMPLOYEES) == [
        "E201",
        "E202",
        "E203",
        "E204",
        "E205",
        "E207",
        "E208",
        "E209",
        "E210",
        "E211",
        "E212",
    ]


@pytest.mark.parametrize(
    ("employee_id", "role", "hire_date", "equipment"),
    [
        (
            "E201",
            "manager",
            "2019-06-01",
            [{"item": "monitor", "issued_on": "2025-01-01"}],
        ),
        (
            "E202",
            "standard",
            "2018-03-01",
            [{"item": "monitor", "issued_on": "2023-08-01"}],
        ),
        (
            "E203",
            "standard",
            "2018-03-01",
            [{"item": "monitor", "issued_on": "2024-01-15"}],
        ),
        ("E204", "standard", "2018-03-01", []),
        ("E205", "standard", "2026-04-01", []),
        ("E207", "standard", "2018-03-01", []),
        (
            "E208",
            "standard",
            "2018-03-01",
            [
                {"item": "monitor", "issued_on": "2020-01-01"},
                {"item": "monitor", "issued_on": "2021-06-01"},
            ],
        ),
        (
            "E209",
            "contractor",
            "2018-03-01",
            [{"item": "monitor", "issued_on": "2022-01-15"}],
        ),
        (
            "E210",
            "standard",
            "2018-03-01",
            [{"item": "monitor", "issued_on": "2023-11-15"}],
        ),
        (
            "E211",
            "manager",
            "2015-01-01",
            [
                {"item": "monitor", "issued_on": "2020-06-01"},
                {"item": "monitor", "issued_on": "2026-06-01"},
            ],
        ),
        ("E212", "director", "2016-05-01", []),
    ],
)
def test_employee_record(employee_id, role, hire_date, equipment) -> None:
    """Each stored employee has the role, hire date, and equipment from the corpus table."""
    record = EMPLOYEES[employee_id]
    assert record["employee_id"] == employee_id
    assert record["role"] == role
    assert record["hire_date"] == hire_date
    assert record["equipment"] == equipment


def test_employees_do_not_store_tenure_years() -> None:
    """Tenure is computed by callers, so no employee record stores tenure_years."""
    for record in EMPLOYEES.values():
        assert "tenure_years" not in record


def test_e999_is_not_a_key() -> None:
    """E999 is the missing-employee id and is absent from the corpus."""
    assert "E999" not in EMPLOYEES


def test_every_stored_issue_date_is_present() -> None:
    """Every stored issue date is a non-empty ISO string."""
    for record in EMPLOYEES.values():
        for unit in record["equipment"]:
            assert isinstance(unit["issued_on"], str) and unit["issued_on"]

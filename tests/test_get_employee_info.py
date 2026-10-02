"""Confirm get_employee_info returns role, tenure, and equipment, or not-found."""

from mcp_vedanti.equipment import get_employee_info


def test_e202_returns_role_tenure_and_monitor() -> None:
    """E202 is standard, tenure 8.6, with one monitor, and no hire date or status."""
    result = get_employee_info("E202")

    assert result == {
        "employee_id": "E202",
        "role": "standard",
        "tenure_years": 8.6,
        "equipment": [{"item": "monitor", "issued_on": "2023-08-01"}],
    }
    assert "hire_date" not in result
    assert "status" not in result


def test_e205_tenure_is_half_a_year() -> None:
    """E205 is standard, tenure 0.5, and has no equipment."""
    result = get_employee_info("E205")

    assert result == {
        "employee_id": "E205",
        "role": "standard",
        "tenure_years": 0.5,
        "equipment": [],
    }


def test_e212_director_with_no_equipment() -> None:
    """E212 is a director, tenure 10.4, with an empty equipment list."""
    result = get_employee_info("E212")

    assert result == {
        "employee_id": "E212",
        "role": "director",
        "tenure_years": 10.4,
        "equipment": [],
    }


def test_e999_is_not_found() -> None:
    """A missing id returns not-found and does not raise."""
    assert get_employee_info("E999") == {
        "employee_id": "E999",
        "status": "not_found",
    }


def test_employee_id_is_case_sensitive() -> None:
    """Employee ids are matched exactly, so e202 is not found."""
    assert get_employee_info("e202") == {
        "employee_id": "e202",
        "status": "not_found",
    }

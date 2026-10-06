"""Confirm get_policy_limits returns a role sheet, or not-found for an unknown role."""

from mcp_vedanti.equipment import get_policy_limits


STANDARD_SHEET = {
    "role": "standard",
    "items": [
        {"item": "monitor", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 4, "min_tenure_years": 1},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ],
}

MANAGER_SHEET = {
    "role": "manager",
    "items": [
        {"item": "monitor", "max_count": 2, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "dock", "max_count": 1, "refresh_years": 4, "min_tenure_years": 0},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ],
}

DIRECTOR_SHEET = {
    "role": "director",
    "items": [
        {"item": "monitor", "max_count": 2, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "dock", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ],
}


def test_standard_sheet() -> None:
    """Standard is monitor 1/3/0, laptop 1/4/1, and headset 1/3/0, with no dock."""
    result = get_policy_limits("standard")

    assert result == STANDARD_SHEET
    assert all(row["item"] != "dock" for row in result["items"])


def test_manager_sheet() -> None:
    """Manager is monitor 2/3/0, laptop 1/2/0, dock 1/4/0, and headset 1/3/0."""
    assert get_policy_limits("manager") == MANAGER_SHEET


def test_director_sheet() -> None:
    """Director is monitor 2/2/0, laptop 1/2/0, dock 1/3/0, and headset 1/3/0."""
    assert get_policy_limits("director") == DIRECTOR_SHEET


def test_role_is_stripped_and_lowercased() -> None:
    """Surrounding whitespace and capitals normalize to the manager sheet."""
    assert get_policy_limits(" Manager ") == MANAGER_SHEET


def test_unknown_roles_are_not_found() -> None:
    """Contractor and intern have no sheet and return not-found without raising."""
    assert get_policy_limits("contractor") == {
        "role": "contractor",
        "status": "not_found",
    }
    assert get_policy_limits("intern") == {
        "role": "intern",
        "status": "not_found",
    }


def test_found_sheet_has_every_row_and_no_decision() -> None:
    """A found sheet lists every item, including a tenure gate of 1, and makes no yes or no decision."""
    result = get_policy_limits("standard")

    assert set(result) == {"role", "items"}
    assert "employee_id" not in result
    assert [row["item"] for row in result["items"]] == ["monitor", "laptop", "headset"]
    laptop = next(row for row in result["items"] if row["item"] == "laptop")
    assert laptop["min_tenure_years"] == 1
    for row in result["items"]:
        assert set(row) == {"item", "max_count", "refresh_years", "min_tenure_years"}
        assert isinstance(row["min_tenure_years"], int)

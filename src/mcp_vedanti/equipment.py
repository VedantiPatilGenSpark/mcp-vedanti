"""Equipment lookups, eligibility, and the in-memory escalation store."""

import datetime

from mcp_vedanti.data import AS_OF, CATALOG_ITEMS, EARLY_REQUEST_DAYS, EMPLOYEES, POLICY


def _tenure_years(hire_date: str) -> float:
    """Years employed as of AS_OF, rounded to one decimal."""
    hired = datetime.date.fromisoformat(hire_date)
    return round((AS_OF - hired).days / 365.25, 1)


def get_employee_info(employee_id: str) -> dict:
    """Return role, tenure, and equipment for one employee."""
    record = EMPLOYEES.get(employee_id)
    if record is None:
        return {"employee_id": employee_id, "status": "not_found"}
    return {
        "employee_id": record["employee_id"],
        "role": record["role"],
        "tenure_years": _tenure_years(record["hire_date"]),
        "equipment": [dict(unit) for unit in record["equipment"]],
    }


def _normalize(value: str) -> str:
    """Strip surrounding whitespace and lowercase a role or item."""
    return value.strip().lower()


def _policy_sheet(role: str) -> tuple[str, list[dict] | None]:
    """The normalized role and a copy of that sheet, or None when there is no sheet."""
    normalized = _normalize(role)
    items = POLICY.get(normalized)
    if items is None:
        return normalized, None
    return normalized, [dict(row) for row in items]


def get_policy_limits(role: str) -> dict:
    """Return the policy sheet for one role."""
    normalized, items = _policy_sheet(role)
    if items is None:
        return {"role": normalized, "status": "not_found"}
    return {
        "role": normalized,
        "items": items,
    }


_OUTCOMES = {
    "not_found": "No employee {employee_id} is on file.",
    "no_policy_sheet": "Role {role_label} has no policy sheet.",
    "not_in_catalog": "Item '{item}' is not in the catalog.",
    "not_on_sheet": "Item {item} is not on the {role_label} sheet.",
    "tenure_below_minimum": (
        "Tenure is {tenure_years} years, below the minimum of {min_tenure_years} year."
    ),
    "count_over_max": "Count {count_on_file} is above the maximum of {max_count}.",
    "under_cap": (
        "Has {count_on_file} {item}. {role_label} limit is {max_count}. "
        "Count is under the limit."
    ),
    "missing_issue_date": "A {item} on file has no issue date.",
    "split_history": (
        "Oldest was issued {oldest_issued_on} and is due. "
        "Newest was issued {newest_issued_on} and is not."
    ),
    "refresh_due": (
        "Has {count_on_file} {item} issued {newest_issued_on}. "
        "{role_label} limit is {max_count} every {refresh_years} years. Refresh is due."
    ),
    "inside_buffer": (
        "Refresh is not due. The request is inside the "
        "{early_request_days}-day early-request buffer."
    ),
    "too_soon": "Refresh is not due. The due date is more than {early_request_days} days away.",
}


def _reason(outcome: str, **fields: object) -> str:
    """Fill the sentence for one eligibility outcome."""
    return _OUTCOMES[outcome].format(**fields)


def _issued_on(unit: dict) -> datetime.date | None:
    """Parse an issue date. A blank value stays missing."""
    value = unit.get("issued_on")
    if not value:
        return None
    return datetime.date.fromisoformat(value)


def _due_on(issued: datetime.date, refresh_years: int) -> datetime.date:
    """Return the issue date plus refresh_years calendar years."""
    try:
        return issued.replace(year=issued.year + refresh_years)
    except ValueError:
        return issued.replace(year=issued.year + refresh_years, day=28)


def _facts(
    role: str,
    tenure_years: float,
    count_on_file: int,
    newest_issued_on: str | None,
    rule: dict | None,
) -> dict:
    """Facts known for this employee and item. Policy numbers stay empty when there is no row."""
    if rule is None:
        max_count = refresh_years = min_tenure_years = None
    else:
        max_count = rule["max_count"]
        refresh_years = rule["refresh_years"]
        min_tenure_years = rule["min_tenure_years"]
    return {
        "role": role,
        "tenure_years": tenure_years,
        "count_on_file": count_on_file,
        "newest_issued_on": newest_issued_on,
        "max_count": max_count,
        "refresh_years": refresh_years,
        "min_tenure_years": min_tenure_years,
    }


def _result(
    employee_id: str,
    item: str,
    status: str,
    reason: str,
    facts: dict | None = None,
) -> dict:
    """One eligibility result. within_policy is None unless the status is clear."""
    if status == "in_policy":
        within_policy = True
    elif status == "out_of_policy":
        within_policy = False
    else:
        within_policy = None
    result = {
        "employee_id": employee_id,
        "item": item,
        "within_policy": within_policy,
        "status": status,
        "reason": reason,
    }
    if facts is not None:
        result["facts"] = facts
    return result


def _dated_units(units: list[dict]) -> list[tuple[datetime.date, str]]:
    """Issue dates that are present, oldest first, keeping the stored date string."""
    dated = []
    for unit in units:
        issued = _issued_on(unit)
        if issued is not None:
            dated.append((issued, unit["issued_on"]))
    dated.sort()
    return dated


def check_request_eligibility(employee_id: str, item: str) -> dict:
    """Classify one employee and item against that role's sheet."""
    normalized_item = _normalize(item)
    info = get_employee_info(employee_id)
    if "status" in info:
        return _result(
            employee_id,
            normalized_item,
            "not_found",
            _reason("not_found", employee_id=employee_id),
        )

    role = info["role"]
    role_label = role.capitalize()
    tenure_years = info["tenure_years"]
    units = [unit for unit in info["equipment"] if _normalize(unit["item"]) == normalized_item]
    count_on_file = len(units)
    dated_on_file = _dated_units(units)
    newest_issued_on = dated_on_file[-1][1] if dated_on_file else None
    _, sheet = _policy_sheet(role)

    if sheet is None:
        return _result(
            employee_id,
            normalized_item,
            "indeterminate",
            _reason("no_policy_sheet", role_label=role_label),
            _facts(role, tenure_years, count_on_file, newest_issued_on, None),
        )

    if normalized_item not in CATALOG_ITEMS:
        return _result(
            employee_id,
            normalized_item,
            "indeterminate",
            _reason("not_in_catalog", item=normalized_item),
            _facts(role, tenure_years, count_on_file, newest_issued_on, None),
        )

    rule = next((row for row in sheet if row["item"] == normalized_item), None)
    facts = _facts(role, tenure_years, count_on_file, newest_issued_on, rule)
    if rule is None:
        return _result(
            employee_id,
            normalized_item,
            "out_of_policy",
            _reason("not_on_sheet", item=normalized_item, role_label=role_label),
            facts,
        )

    if tenure_years < rule["min_tenure_years"]:
        return _result(
            employee_id,
            normalized_item,
            "out_of_policy",
            _reason(
                "tenure_below_minimum",
                tenure_years=tenure_years,
                min_tenure_years=rule["min_tenure_years"],
            ),
            facts,
        )

    if count_on_file > rule["max_count"]:
        return _result(
            employee_id,
            normalized_item,
            "indeterminate",
            _reason(
                "count_over_max",
                count_on_file=count_on_file,
                max_count=rule["max_count"],
            ),
            facts,
        )

    if count_on_file < rule["max_count"]:
        return _result(
            employee_id,
            normalized_item,
            "in_policy",
            _reason(
                "under_cap",
                count_on_file=count_on_file,
                item=normalized_item,
                role_label=role_label,
                max_count=rule["max_count"],
            ),
            facts,
        )

    if any(_issued_on(unit) is None for unit in units):
        facts = _facts(role, tenure_years, count_on_file, None, rule)
        return _result(
            employee_id,
            normalized_item,
            "indeterminate",
            _reason("missing_issue_date", item=normalized_item),
            facts,
        )

    dated = _dated_units(units)
    oldest_issued, oldest_text = dated[0]
    newest_issued, newest_text = dated[-1]
    facts = _facts(role, tenure_years, count_on_file, newest_text, rule)
    refresh_years = rule["refresh_years"]
    oldest_due = _due_on(oldest_issued, refresh_years) <= AS_OF
    newest_due_on = _due_on(newest_issued, refresh_years)
    if len(dated) > 1 and oldest_due and newest_due_on > AS_OF:
        return _result(
            employee_id,
            normalized_item,
            "indeterminate",
            _reason(
                "split_history",
                oldest_issued_on=oldest_text,
                newest_issued_on=newest_text,
            ),
            facts,
        )

    if newest_due_on <= AS_OF:
        return _result(
            employee_id,
            normalized_item,
            "in_policy",
            _reason(
                "refresh_due",
                count_on_file=count_on_file,
                item=normalized_item,
                newest_issued_on=newest_text,
                role_label=role_label,
                max_count=rule["max_count"],
                refresh_years=refresh_years,
            ),
            facts,
        )

    if (newest_due_on - AS_OF).days <= EARLY_REQUEST_DAYS:
        return _result(
            employee_id,
            normalized_item,
            "indeterminate",
            _reason("inside_buffer", early_request_days=EARLY_REQUEST_DAYS),
            facts,
        )

    return _result(
        employee_id,
        normalized_item,
        "out_of_policy",
        _reason("too_soon", early_request_days=EARLY_REQUEST_DAYS),
        facts,
    )


escalations: list[dict] = []


def flag_for_human_review(employee_id: str, request: str, reason: str) -> dict:
    """Append one escalation ticket and return a copy of the stored record."""
    record = {
        "escalation_id": f"ESC-{len(escalations) + 1}",
        "employee_id": employee_id,
        "request": request,
        "reason": reason,
    }
    escalations.append(record)
    return dict(record)


def reset_escalations() -> None:
    """Clear the in-memory escalation list."""
    escalations.clear()

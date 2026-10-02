"""Equipment lookups, eligibility, and the in-memory escalation store."""

import datetime

from mcp_vedanti.data import AS_OF, EMPLOYEES


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


def get_policy_limits(role: str) -> dict:
    """Return the policy sheet for one role."""
    raise NotImplementedError


def check_request_eligibility(employee_id: str, item: str) -> dict:
    """Classify one employee and item against that role's sheet."""
    raise NotImplementedError


def flag_for_human_review(employee_id: str, request: str, reason: str) -> dict:
    """Append one escalation ticket and return the stored copy."""
    raise NotImplementedError


def reset_escalations() -> None:
    """Clear the in-memory escalation list."""
    raise NotImplementedError

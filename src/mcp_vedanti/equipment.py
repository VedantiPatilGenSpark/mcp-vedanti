"""Equipment lookups, eligibility, and the in-memory escalation store."""


def get_employee_info(employee_id: str) -> dict:
    """Return role, tenure, and equipment for one employee."""
    raise NotImplementedError


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

# PRD: server logic, with Vedanti

This work is done. The four functions, `reset_escalations`, and MCP registration match the behavior below. The check order and the reason sentences as built are in `docs/implementation-decisions.md`.

The tests and the mock data were already written. They were not edited to make a test pass. `src/mcp_vedanti/equipment.py` holds the functions. `src/mcp_vedanti/server.py` registers the four tools.

## Behavior

Import `AS_OF`, `EARLY_REQUEST_DAYS`, `CATALOG_ITEMS`, `POLICY`, and `EMPLOYEES` from `mcp_vedanti.data`. Do not copy the sheets or the people into `equipment.py`.

Normalize role and item by stripping surrounding whitespace and lowercasing. Then match the catalog. Leave employee ids unchanged.

Tenure is `(AS_OF - hire_date).days / 365.25`, rounded to one decimal. Return `tenure_years`. Do not return `hire_date`.

`get_employee_info` and `get_policy_limits` return a `status: not_found` dict for an unknown id or role. They do not raise.

`check_request_eligibility` follows the order in `docs/prd-tests.md`. Under the cap, a missing issue date does not escalate. At the cap, a unit of that item with no `issued_on` is `indeterminate` before split history is considered, and split history is decided before the 90-day buffer. The seed data has no blank date. That branch is a guard so a blank date is not turned into a guessed due date. `within_policy` is `None` for `indeterminate` and `not_found`. The due date is `issued_on` plus `refresh_years` calendar years. February 29 in a year that has no February 29 becomes February 28.

The escalation store is a list in this module. `flag_for_human_review` appends one record and returns a copy of that record. The agent calls it only for `indeterminate` and `not_found`. `reason` is a required string and is stored as given. Ids are `ESC-1`, then `ESC-2`, counting only what is currently stored. `reset_escalations` clears the list. An unknown employee id is still stored. This function does not read policy and does not change `EMPLOYEES`.

## Done when

`tests/test_corpus.py` and the four function test files pass. `server.py` registers `get_employee_info`, `get_policy_limits`, `check_request_eligibility`, and `flag_for_human_review`. The throwaway `add` tool is not registered. `reset_escalations` is not a tool.

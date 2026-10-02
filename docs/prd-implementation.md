# PRD: server logic, with Vedanti

Implement the four plain functions until the existing tests pass. The tests and the mock data are already written. Do not edit them. If a test fails, change the implementation.

Read `requirements.md`, `docs/decisions.md`, `docs/prd-mock-data.md`, and `docs/prd-tests.md` before writing code. The test PRD is the contract, including the check order and the reason fragments.

Work one function at a time, with Vedanti. After a function's tests pass, stop and wait before starting the next. Do not commit unless Vedanti asks.

## Files you may edit

- `src/mcp_vedanti/equipment.py` — the four functions and `reset_escalations`.
- `src/mcp_vedanti/server.py` — only in the last step, after every plain-function test passes.

Do not edit `src/mcp_vedanti/data.py`, anything under `tests/`, `requirements.md`, or the decision record.

## Order of work

1. Add `equipment.py` with `get_employee_info`, `get_policy_limits`, `check_request_eligibility`, `flag_for_human_review`, and `reset_escalations`. Bodies may raise `NotImplementedError` so the suite collects. Then stop.
2. Implement `get_employee_info` until `tests/test_get_employee_info.py` passes.
3. Implement `get_policy_limits` until `tests/test_get_policy_limits.py` passes.
4. Implement `check_request_eligibility` until `tests/test_check_request_eligibility.py` passes.
5. Implement `flag_for_human_review` and `reset_escalations` until `tests/test_flag_for_human_review.py` passes.
6. Only then, and only if Vedanti says to continue, register the four functions as MCP tools on the server in `server.py`. Remove the throwaway `add` tool in that same step. Do not register `add` and the real tools together.

Run the relevant test file after each step. Do not weaken a test to get a pass.

## Behavior

Import `AS_OF`, `EARLY_REQUEST_DAYS`, `CATALOG_ITEMS`, `POLICY`, and `EMPLOYEES` from `mcp_vedanti.data`. Do not copy the sheets or the people into `equipment.py`.

Normalize role and item by stripping surrounding whitespace and lowercasing. Then match the catalog. Leave employee ids unchanged.

Tenure is `(AS_OF - hire_date).days / 365.25`, rounded to one decimal. Return `tenure_years`. Do not return `hire_date`.

`get_employee_info` and `get_policy_limits` return a `status: not_found` dict for an unknown id or role. They do not raise.

`check_request_eligibility` follows the order in `docs/prd-tests.md`. At `max_count`, split history is decided before the 90-day buffer. Under the cap, a missing issue date does not escalate. `within_policy` is `None` for `indeterminate` and `not_found`.

The escalation store is a list in this module. `flag_for_human_review` appends one record and returns that record. Ids are `ESC-1`, then `ESC-2`, counting only what is currently stored. `reset_escalations` clears the list. An unknown employee id is still stored. This function does not read policy and does not change `EMPLOYEES`.

## Done when

`tests/test_corpus.py` and the four function test files pass. `server.py` is unchanged until Vedanti asks for the MCP registration step.

# PRD: server unit tests

These tests are the contract for the server functions. They were written before the functions existed. The functions now pass them. Do not weaken a test to match a later change in the server.

The behavior under test is `docs/prd/requirements.md`. The records under test are `docs/prd/mock-data.md`. Use those employee ids, dates, and tenure numbers. Do not add a person, and do not compute an expected status by calling the function under test.

Plain functions only. Do not open an MCP client or a running server.

## Files

| File | Covers |
|---|---|
| `tests/test_corpus.py` | The data module only. |
| `tests/test_get_employee_info.py` | `get_employee_info` |
| `tests/test_get_policy_limits.py` | `get_policy_limits` |
| `tests/test_check_request_eligibility.py` | `check_request_eligibility` |
| `tests/test_flag_for_human_review.py` | `flag_for_human_review` and `reset_escalations` |

Leave `tests/test_package.py` as it is.

Corpus tests import `mcp_vedanti.data`. The other files import the functions from `mcp_vedanti.equipment`. Eligibility tests may read `mcp_vedanti.data` for ids and raw records. Expected `status`, `within_policy`, tenure, and sheet numbers are written out in the test, not derived from production code.

## What every eligibility result means

`within_policy` is `true`, `false`, or `None`. `status` is `in_policy`, `out_of_policy`, `indeterminate`, or `not_found`.

For `in_policy` and `out_of_policy`, `facts` includes `role`, `tenure_years`, `count_on_file`, `newest_issued_on`, `max_count`, `refresh_years`, and `min_tenure_years`. `newest_issued_on` is `None` when the person has no units of that item.

`reason` is a string. Assert that it contains the facts named in each case below. Do not lock the whole sentence.

Checks run in this order. Each fixture below is built so only one of them applies:

1. Unknown `employee_id` → `not_found`.
2. Role has no sheet → `indeterminate`.
3. Item is not in the catalog → `indeterminate`.
4. Item is not on that role's sheet → `out_of_policy`.
5. Tenure is below `min_tenure_years` → `out_of_policy`.
6. Count of that item is above `max_count` → `indeterminate`.
7. Count is under `max_count` → `in_policy`. Issue dates are not required on this path.
8. Count equals `max_count`: missing `issued_on` → `indeterminate`; otherwise split history → `indeterminate`; otherwise newest unit due on or before 2026-10-01 → `in_policy`; otherwise the as-of date is inside the 90 days before the due date → `indeterminate`; otherwise `out_of_policy`.

The due date is `issued_on` plus `refresh_years` calendar years. Split history means more than one unit, the oldest is already due, and the newest is not. It is decided before the 90-day buffer. A tenure shortfall is a denial and is not pulled into the buffer.

Role and item arguments are stripped and lowercased before the catalog match. Employee ids are exact and keep their case.

## `tests/test_corpus.py`

Assert the exports from `docs/prd/mock-data.md`:

- `AS_OF` is 2026-10-01 and `EARLY_REQUEST_DAYS` is 90.
- Catalog items are monitor, laptop, dock, and headset, and do not include keyboard.
- Policy roles are standard, manager, and director, and do not include contractor.
- The three sheets match the `max_count` / `refresh_years` / `min_tenure_years` table in that PRD, including the missing standard dock row.
- The employee ids are exactly E201 through E205 and E207 through E212. There is no E206.
- Every stored `issued_on` is a non-empty date string.
- Each employee's role, hire date, and equipment match that table.
- No `tenure_years` field is stored on an employee.
- `E999` is not a key.

## `tests/test_get_employee_info.py`

- E202 returns role `standard`, `tenure_years` `8.6`, and one monitor issued `2023-08-01`. The result has no `hire_date` and no `status`.
- E205 returns `tenure_years` `0.5`.
- E212 returns role `director`, `tenure_years` `10.4`, and an empty equipment list.
- `E999` returns `{"employee_id": "E999", "status": "not_found"}` and does not raise.
- `"e202"` returns not-found. Ids are not lowercased.

## `tests/test_get_policy_limits.py`

- `standard` returns monitor `1 / 3 / 0`, laptop `1 / 4 / 1`, and headset `1 / 3 / 0`, and no dock.
- `manager` returns monitor `2 / 3 / 0`, laptop `1 / 2 / 0`, dock `1 / 4 / 0`, and headset `1 / 3 / 0`.
- `director` returns monitor `2 / 2 / 0`, laptop `1 / 2 / 0`, dock `1 / 3 / 0`, and headset `1 / 3 / 0`.
- `" Manager "` returns the manager sheet.
- `contractor` and `intern` each return `{"role": "<normalized role>", "status": "not_found"}` and do not raise.
- A found sheet has no employee id, no yes or no, and every item row, including rows with `min_tenure_years` of 1.

## `tests/test_check_request_eligibility.py`

One test per row. Assert `status`, `within_policy`, and the facts or reason fragments named here.

| Call | Result | What the reason or facts must show |
|---|---|---|
| E201, monitor | `in_policy`, true | Count 1, max 2. Under the cap even though the 2025 monitor is not due. |
| E201, `" Monitor "` | same as E201, monitor | Normalization. Item in the result is `monitor`. |
| E202, monitor | `in_policy`, true | Newest issued `2023-08-01`, refresh 3. Due date is already past. |
| E203, monitor | `out_of_policy`, false | Due date is more than 90 days away. |
| E204, dock | `out_of_policy`, false | Dock is absent from the standard sheet. |
| E205, laptop | `out_of_policy`, false | Tenure 0.5, minimum 1. |
| E205, monitor | `in_policy`, true | Same person. Monitor minimum is 0 and the count is 0. |
| A temporary standard employee at the monitor cap, inserted by the test and removed before the test ends, with `issued_on` None | `indeterminate`, None | Issue date is missing. This person is not part of the seed corpus. |
| E207, headset | `in_policy`, true | Count 0, max 1. Headset is on the standard sheet. |
| E207, keyboard | `indeterminate`, None | Keyboard is not in the catalog. |
| E208, monitor | `indeterminate`, None | Count 2 is over the max of 1. |
| E209, monitor | `indeterminate`, None | Contractor has no policy sheet. |
| E210, monitor | `indeterminate`, None | Due date `2026-11-15` is inside the 90-day buffer. Reason contains `90`. |
| E211, monitor | `indeterminate`, None | Reason contains both `2020-06-01` and `2026-06-01`. |
| E999, monitor | `not_found`, None | Reason contains `E999`. |
| E999, keyboard | `not_found`, None | Missing employee is decided before the unknown item. |

## `tests/test_flag_for_human_review.py`

Import `flag_for_human_review` and `reset_escalations` from `mcp_vedanti.equipment`. Call `reset_escalations` at the start of each test.

- One call stores one record and returns that same record, with `escalation_id` `ESC-1`, plus the employee id, request text, and reason that were passed in.
- A second call in the same test returns `ESC-2`. The store holds both, in that order.
- After `reset_escalations`, the next id is `ESC-1` again.
- `flag_for_human_review("E999", "I need a monitor.", "No employee E999")` stores the ticket. It does not return not-found.
- Filing a ticket does not change E202's equipment list in the data module.

The test file does not approve, deny, or decide who should be flagged. It only checks that the store appends a copy of what it was given.

## Done when

The five test modules exist, every row above has a test, and those tests pass against `data.py` and `equipment.py`. Corpus tests assert the records in `docs/prd/mock-data.md`. The function tests do not open an MCP client.

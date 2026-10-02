# Implementation decisions

How the finished server in `src/mcp_vedanti/equipment.py` and `src/mcp_vedanti/server.py` behaves. `docs/decisions.md` locks the product rules. This file records how those rules are built, including the check order and the reason sentences.

The functions stay plain. `server.py` registers four of them as MCP tools and does not contain the rules.

Data comes from `mcp_vedanti.data`. The sheets and the people are not copied into this module. Role and item arguments are stripped and lowercased, then matched exactly. Employee ids are not normalized.

## `get_employee_info`

Lookup is `EMPLOYEES.get(employee_id)`. A missing id returns `employee_id` and `status: not_found` and does not raise. `"e202"` is missing because the id is not lowercased.

A found record returns `employee_id`, `role`, `tenure_years`, and `equipment`. It has no `hire_date` and no `status`. Tenure is `(AS_OF - hire_date).days / 365.25`, rounded to one decimal, in `_tenure_years`. Equipment is a new list of new dicts, so a caller cannot change the stored units by editing the result.

## `get_policy_limits`

The role is normalized, then used as a key in `POLICY`. A missing role, including `contractor`, returns the normalized role and `status: not_found`. A found sheet returns `role` and `items` only. Item order is the order stored on the sheet. Each row is copied. Rows with `min_tenure_years` of 1 stay on the sheet. This function does not look at an employee.

## `check_request_eligibility`

The function loads the person through `get_employee_info` and the sheet from `POLICY`. The caller cannot pass a role or a history. The item in the result is the normalized item. The role in `facts` is the stored role. The role in a sentence is capitalized, so `standard` reads as `Standard`.

`within_policy` is `true` for `in_policy`, `false` for `out_of_policy`, and `None` for `indeterminate` and `not_found`. A missing employee has no `facts`. Every other result includes the facts known at that point. Policy numbers are `None` when there is no matching row.

### Check order

The first match returns. Later checks do not run.

1. **Unknown employee.** `get_employee_info` reports `not_found`. Status is `not_found`. This runs before the catalog check, so `E999` asking for a headset is still `not_found`.
2. **Role has no sheet.** `POLICY` has no entry for the role. Status is `indeterminate`. `contractor` stops here, including when the item is also unknown.
3. **Item is not in the catalog.** Status is `indeterminate`. `headset` is not a denial. The sheet is not consulted.
4. **Item is not on this role's sheet.** The item is in the catalog and absent from the sheet. Status is `out_of_policy`. A standard dock stops here.
5. **Tenure is below `min_tenure_years`.** Comparison is `<`. Status is `out_of_policy`. This runs before the count checks, so a short tenure stays a denial. The 90-day buffer does not open it. E205's laptop stops here. The same person's monitor has a minimum of 0, so it continues.
6. **Count is above `max_count`.** Status is `indeterminate`. The file already holds more units than the sheet allows, so approving or denying would be a guess. E208's two monitors, against a standard cap of 1, stop here. Issue dates are not read.
7. **Count is under `max_count`.** Status is `in_policy`. The role still has room for another unit, so issue dates are not required and a blank date does not escalate. E201's one monitor against a manager cap of 2 stops here even though that monitor is not due.
8. **Count equals `max_count`.** This is a replacement. Decide in this order:
   1. **Missing `issued_on`.** Any unit of this item has no issue date. Status is `indeterminate`. `newest_issued_on` is `None`. No due date is calculated. The seed data has no such unit. The test inserts one and removes it.
   2. **Split history.** More than one unit, the oldest due date is on or before `AS_OF`, and the newest due date is after `AS_OF`. Status is `indeterminate`. One unit cannot split, because the oldest and the newest are the same object. This runs before the buffer. E211 stops here.
   3. **Refresh is due.** The newest due date is on or before `AS_OF`. Status is `in_policy`. E202 stops here.
   4. **Early-request buffer.** The number of days from `AS_OF` to the newest due date is from 1 through `EARLY_REQUEST_DAYS` (90). Status is `indeterminate`. E210 stops here.
   5. **Too soon.** The due date is more than 90 days away. Status is `out_of_policy`. E203 stops here.

The due date is the issue date plus `refresh_years` calendar years. February 29 in a year that has no February 29 becomes February 28. The refresh clock is the issue date of units of this item, not the date of a previous request.

### Reason sentences

The decision tree picks an outcome key. It does not build a sentence inline. `_OUTCOMES` holds one sentence per key, and `_reason` fills it. `facts` carries the labeled numbers. `reason` is the sentence the assistant quotes.

| Outcome | Sentence |
|---|---|
| `not_found` | No employee {employee_id} is on file. |
| `no_policy_sheet` | Role {role_label} has no policy sheet. |
| `not_in_catalog` | Item '{item}' is not in the catalog. |
| `not_on_sheet` | Item {item} is not on the {role_label} sheet. |
| `tenure_below_minimum` | Tenure is {tenure_years} years, below the minimum of {min_tenure_years} year. |
| `count_over_max` | Count {count_on_file} is above the maximum of {max_count}. |
| `under_cap` | Has {count_on_file} {item}. {role_label} limit is {max_count}. Count is under the limit. |
| `missing_issue_date` | A {item} on file has no issue date. |
| `split_history` | Oldest was issued {oldest_issued_on} and is due. Newest was issued {newest_issued_on} and is not. |
| `refresh_due` | Has {count_on_file} {item} issued {newest_issued_on}. {role_label} limit is {max_count} every {refresh_years} years. Refresh is due. |
| `inside_buffer` | Refresh is not due. The request is inside the {early_request_days}-day early-request buffer. |
| `too_soon` | Refresh is not due. The due date is more than {early_request_days} days away. |

## `flag_for_human_review` and `reset_escalations`

Tickets live in the module-level list `escalations`. Each call appends one record and returns a new dict with the same fields, so the caller cannot change the stored ticket by editing the return value. The id is `ESC-` plus the count of tickets currently in the list, starting at `ESC-1`. `reset_escalations` clears the list, so the next id is `ESC-1` again. The id is not a counter that keeps growing across resets.

The record stores `employee_id`, `request`, and `reason` as they were passed. An unknown employee id is stored. The return value has no `status`. This function does not read `POLICY` or `EMPLOYEES`, and it does not change either one.

## MCP registration

`server.py` registers the four functions with `mcp.tool()`: `get_employee_info`, `get_policy_limits`, `check_request_eligibility`, and `flag_for_human_review`. The tool name, parameters, and docstring are the function's own. The throwaway `add` tool is gone. `reset_escalations` is not a tool. A missing or wrong-typed argument is rejected by the tool schema before the function runs.

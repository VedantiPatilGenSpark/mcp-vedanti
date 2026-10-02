# Working decisions

Design record for the rules in `requirements.md`. Server business rules below are locked.

## Catalog

Roles: `standard`, `manager`, `director`.

Items: `monitor`, `laptop`, `dock`.

`headset` is not in the catalog. A request for it is an unknown item.

Before a role or item is stored or compared, preprocessing strips surrounding whitespace and lowercases it. `Monitor` and ` monitor ` become `monitor`. The result is then matched against the enum exactly. `head set` does not become `headset`. `Manager` becomes `manager`.

## Policy sheets

`max_count` / `refresh_years` / `min_tenure_years`.

| Role | monitor | laptop | dock |
|---|---|---|---|
| standard | 1 / 3 / 0 | 1 / 4 / 1 | not on this sheet |
| manager | 2 / 3 / 0 | 1 / 2 / 0 | 1 / 4 / 0 |
| director | 2 / 2 / 0 | 1 / 2 / 0 | 1 / 3 / 0 |

A standard employee asking for a dock is `out_of_policy`, because dock is a known item and it is missing from that sheet. Laptop refresh differs by role (4 vs 2). Monitor refresh differs for director (2 vs 3). Dock refresh differs for director (3 vs 4).

Tenure is computed from `hire_date` against the fixed as-of date `2026-10-01`. `tenure_years` is `(as_of - hire_date).days / 365.25`, rounded to one decimal. `get_employee_info` returns `tenure_years` only. `hire_date` stays in the mock data.

## Cases the mock data must be able to produce

- In policy because the count is under `max_count`.
- In policy because the newest unit is at least `refresh_years` old.
- Out of policy because the newest unit comes due more than 90 days after the as-of date.
- Indeterminate because the person is at `max_count` and the due date is inside the next 90 days.
- Indeterminate because the person is at `max_count` and the oldest unit is already due while the newest is not.
- Out of policy because the item is not on that role's sheet.
- Out of policy because tenure is below `min_tenure_years`.
- Indeterminate because the item is not in the catalog (`headset`).
- Indeterminate because the count on file is already over `max_count`.
- Indeterminate because the employee exists but their role has no policy sheet. That fixture role is `contractor`. It is stored on the employee and is not one of `standard`, `manager`, or `director`. `get_policy_limits("contractor")` is not-found. Eligibility for that employee is indeterminate.
- Not found for an unknown `employee_id`.
- Not found for an unknown role passed to `get_policy_limits`.

## Request the agent extracts

Tools supply role, tenure, equipment, policy, and eligibility. The request does not supply those.

| Field | Meaning |
|---|---|
| `employee_id` | Who is asking. Argument to the lookup tools. |
| `item` | What they want. An enum value. |
| `reason` | The employee's own justification, free text. |

There is no `requested` field. There is no trusted `role` field. Text that claims a role is a claim, checked against `get_employee_info`.

The employee's `reason` is not the `reason` passed to `flag_for_human_review`. The flag reason is why a human must review.

## `get_employee_info(employee_id)`

Returns the record on file. A missing id does not raise. The function returns a normal not-found result with no record fields:

```json
{"employee_id": "E999", "status": "not_found"}
```

Tests cover a real id and a missing id. `hire_date` is not part of this return.

```json
{
  "employee_id": "E202",
  "role": "standard",
  "tenure_years": 8.6,
  "equipment": [
    {"item": "monitor", "issued_on": "2023-08-01"}
  ]
}
```

`role` is the string value of a role enum.

`tenure_years` is time employed, not the age of a device. Mock data stores `hire_date`. The function computes tenure against a fixed as-of date so tests do not drift. Eligibility may use tenure when a role rule sets `min_tenure_years`.

`equipment` is one entry per unit already issued. Two monitors are two objects so each keeps its own `issued_on`. A count map such as `{"monitor": 2}` drops the dates the refresh rules need. Count is derived from this list.

## `get_policy_limits(role)`

The rule sheet for a role. No employee, no dates, no yes or no. An unknown role does not raise. The function returns a normal not-found result:

```json
{"role": "intern", "status": "not_found"}
```

```json
{
  "role": "standard",
  "items": [
    {
      "item": "monitor",
      "max_count": 1,
      "refresh_years": 3,
      "min_tenure_years": 0
    }
  ]
}
```

`items` is what that role may request. The wait period is `refresh_years` on each item. One period for the whole role cannot express "monitor every 3 years, laptop every 2 years." This function still takes only `role`.

The same item may also differ across roles. `monitor` on `standard` is 3 years while `monitor` on `director` is 2. The mock data uses that difference so tests cover both sheets.

`max_count` is how many units of that item the role may have on file. `min_tenure_years` is the threshold written on the rule, not a check this function runs. This function has no employee, so it does not know anyone's tenure and it does not drop items. `0` means the threshold does not block. `check_request_eligibility` is what compares `tenure_years` with `min_tenure_years`.

## `check_request_eligibility(employee_id, item)`

Looks up the employee and that role's rule internally. The agent cannot pass in a role or a history. The agent still calls the two lookup tools itself so the trace shows the investigation.

The first match returns.

1. Unknown `employee_id` → `not_found`. No `facts`. This wins even when the item is `headset`.
2. Role has no sheet → `indeterminate`.
3. Item is not in the catalog → `indeterminate`.
4. Item is known but not on this role's sheet → `out_of_policy`.
5. Tenure is below `min_tenure_years` → `out_of_policy`. The buffer does not open this.
6. Count of that item is above `max_count` → `indeterminate`. Issue dates are not read.
7. Count is under `max_count`, and tenure is enough → `in_policy`. The buffer does not apply, because the role still has room for another unit. A blank issue date on this path does not escalate.
8. Count equals `max_count`. The due date is the newest `issued_on` plus `refresh_years` calendar years. February 29 in a year that has no February 29 becomes February 28. The clock is the issue date of equipment on file for this item. It is not the date of the last request of any kind. A server-wide early-request buffer of 90 days sits immediately before that due date. Then:
   1. A unit of that item has no `issued_on` → `indeterminate`. No due date is calculated.
   2. Split history. More than one unit, the oldest is already due, and the newest is not → `indeterminate`. This is checked before the buffer. One unit cannot split.
   3. The newest unit is already due → `in_policy`.
   4. The as-of date is inside the 90 days before the due date → `indeterminate`. The sheet says not yet. A person might still approve it so the unit arrives as the period turns over.
   5. The due date is more than 90 days away → `out_of_policy`.

A tenure shortfall is `out_of_policy` and is not softened by the buffer. One unit cannot be a split history, because the oldest and the newest are the same unit.

| Situation | `within_policy` | `status` |
|---|---|---|
| Item is on the role's list, count is under `max_count`, tenure is enough | `true` | `in_policy` |
| Count is at `max_count`, the newest unit is already due, and this is not a split history | `true` | `in_policy` |
| Item is known but not on this role's list | `false` | `out_of_policy` |
| Count is at `max_count` and the due date is more than 90 days away | `false` | `out_of_policy` |
| Tenure is below `min_tenure_years` | `false` | `out_of_policy` |
| The item is unknown, or the count is already over `max_count` | `null` | `indeterminate` |
| At `max_count`, and a unit of that item has no issue date | `null` | `indeterminate` |
| At `max_count`, oldest unit is due, newest unit is not | `null` | `indeterminate` |
| At `max_count`, and the as-of date is inside the 90 days before the due date | `null` | `indeterminate` |
| Employee exists, and their role has no policy sheet | `null` | `indeterminate` |
| No employee with that id | `null` | `not_found` |

```json
{
  "employee_id": "E202",
  "item": "monitor",
  "within_policy": true,
  "status": "in_policy",
  "reason": "Has 1 monitor issued 2023-08-01. Standard limit is 1 every 3 years. Refresh is due.",
  "facts": {
    "role": "standard",
    "tenure_years": 8.6,
    "count_on_file": 1,
    "newest_issued_on": "2023-08-01",
    "max_count": 1,
    "refresh_years": 3,
    "min_tenure_years": 0
  }
}
```

`facts` holds the labeled numbers. `reason` is one sentence for the outcome that matched. The role in the sentence is capitalized. The sentences are listed in `docs/implementation-decisions.md`.

A bool is not enough. The agent needs `status` so it does not invent the approve, deny, or escalate boundary.

## `flag_for_human_review(employee_id, request, reason)`

Side effect means this function changes state on the server, instead of only computing an answer. The store is a list in the server process. Tests can reset it. The record dies when that process stops. The client does not write the list. It calls the tool, and the return value is a copy of the record the server just appended. Routing to a person, inbox, or ticket system is out of scope.

`request` is the original request text. `reason` is the eligibility sentence for that outcome, passed through by the agent.

An unknown `employee_id` is still stored. The queue can hold a case for a person who is not on file. The call does not return not-found and does not leave the list unchanged.

Returns the stored record, including an id:

```json
{
  "escalation_id": "ESC-1",
  "employee_id": "E207",
  "request": "I need a headset.",
  "reason": "Item 'headset' is not in the catalog."
}
```

`reason` is a required string. The tool stores it and does not accept null. The agent calls this tool only for `indeterminate` and `not_found`. The id is `ESC-` plus the number of tickets currently stored. Clearing the list makes the next id `ESC-1` again. `reset_escalations` clears the list and is not an MCP tool.

## Who decides

The eligibility tool classifies. The agent routes and does not override the status.

| `status` | Agent |
|---|---|
| `in_policy` | Draft an approval. Do not call the flag tool. |
| `out_of_policy` | Draft a denial. Do not call the flag tool. |
| `indeterminate` | Call `flag_for_human_review`. Draft that it was escalated. |
| `not_found` | Call `flag_for_human_review`. Different reason from a policy ambiguity. |

`indeterminate` and `not_found` are normal eligibility results. The tool call succeeds, `within_policy` is `null`, and the agent escalates. They are not client errors. A bad call is only a wrong or missing argument, which the SDK rejects before this function runs. The agent does not treat that SDK error as an eligibility status.

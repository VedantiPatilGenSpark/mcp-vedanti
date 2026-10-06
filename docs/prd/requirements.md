# Equipment request requirements

The server is the IT department's equipment system. An employee does not call it directly. An assistant calls it on their behalf, then writes the reply the employee sees.

The assistant looks up the person and that role's rules, asks whether the request is inside policy, and then approves, denies, or escalates. The server classifies the case. The assistant follows that classification and does not override it.

## What a request contains

The assistant extracts three fields from the employee's message:

| Field | Meaning |
|---|---|
| `employee_id` | Who is asking. This is the key for every lookup. |
| `item` | The equipment they want, after it has been normalized to the catalog. |
| `reason` | Why the employee says they want it. Free text. |

Role, tenure, current equipment, and the policy numbers are not taken from the message. Those come from the server. If the message claims "I am a manager," the role on the employee record is the one that counts.

The host takes `employee_id` from the CLI (`E` plus three digits). It names `item` in one extract call before ReAct. It does not pass the employee's justification into eligibility.

The employee's `reason` is their justification. It is not an input to eligibility. The `reason` stored on an escalation is a different sentence: why a person has to review the case.

## Mock data

Records are synthetic. Dates do not move, because tenure and refresh checks use a fixed as-of date of **2026-10-01**. Tenure is `(as-of date − hire date)` in days, divided by 365.25, rounded to one decimal. `hire_date` stays in the mock data. Callers see `tenure_years` only.

Each employee record holds:

| Field | Meaning |
|---|---|
| `employee_id` | Stable id. |
| `hire_date` | Start date used to compute tenure. |
| `role` | `standard`, `manager`, `director`, or the fixture role `contractor`. |
| `equipment` | Units already issued. One object per unit: `item` and `issued_on`. |

Equipment is a list of units so each one keeps its own issue date. Two monitors are two objects. The count of an item is how many objects in that list use that item name. A count by itself cannot answer "every 3 years," because the dates would be gone.

One employee has role `contractor`. That person is on file and has no policy sheet, so eligibility cannot decide their request. `contractor` is not a role `get_policy_limits` can describe.

Role and item values are normalized before they are stored or compared: surrounding whitespace is removed, and the value is lowercased. `Monitor` and ` monitor ` both become `monitor`. The normalized value must then match the catalog exactly. `head set` does not become `headset`.

## Catalog and policy

Roles with a policy sheet: `standard`, `manager`, `director`.

Catalog items: `monitor`, `laptop`, `dock`, `headset`. `keyboard` is not in the catalog. Asking for a keyboard does not produce a denial. The server cannot tell what policy would apply, so the case is indeterminate. `headphones` is not a catalog key. Server normalize is still only strip and lowercase; `head set` does not become `headset`.

Each role has its own sheet. A sheet does not name an employee and does not say yes or no. For each item the role may request, the sheet gives:

| Field | Meaning |
|---|---|
| `max_count` | How many units of that item this role may have on file. |
| `refresh_years` | How old the newest unit must be before another one is allowed at the cap. |
| `min_tenure_years` | How long the person must have been employed. `0` means tenure does not block that item. |

The same item can have different numbers on different roles. That is deliberate, so a test can show the server followed the role's sheet.

`max_count` / `refresh_years` / `min_tenure_years`:

| Role | monitor | laptop | dock | headset |
|---|---|---|---|---|
| standard | 1 / 3 / 0 | 1 / 4 / 1 | not on this sheet | 1 / 3 / 0 |
| manager | 2 / 3 / 0 | 1 / 2 / 0 | 1 / 4 / 0 | 1 / 3 / 0 |
| director | 2 / 2 / 0 | 1 / 2 / 0 | 1 / 3 / 0 | 1 / 3 / 0 |

A standard employee who asks for a dock is outside policy: dock is a real catalog item, and it is absent from the standard sheet. A standard laptop refreshes every 4 years. A manager or director laptop refreshes every 2. A director's monitor refreshes every 2 years. A standard or manager monitor refreshes every 3. A director's dock refreshes every 3 years. A manager's dock refreshes every 4.

The refresh clock is the issue date of equipment already on file for that item. It is not the date of the person's last request. The due date is the newest `issued_on` plus `refresh_years` calendar years. The server also keeps one early-request buffer of 90 days immediately before that due date. The buffer is the same for every role and item, so the sheets stay readable and a test only has to show that the window exists.

`min_tenure_years` is only a number on the sheet. The policy tool returns every row, including rows a particular employee is too new to use. The eligibility check is what compares the person's `tenure_years` with that number. The only tenure gate in these sheets is the standard laptop, which requires 1 year of employment.

## How eligibility decides

`check_request_eligibility` loads the employee and that role's sheet itself. The caller cannot pass in a role or a history. The first match returns.

1. **Unknown employee.** Status is `not_found`. The result has no `facts`. This wins even when the item is `keyboard`.
2. **Role has no sheet.** Status is `indeterminate`. `contractor` stops here.
3. **Item is not in the catalog.** Status is `indeterminate`. `keyboard` is not a denial.
4. **Item is not on this role's sheet.** Status is `out_of_policy`. A standard dock stops here.
5. **Tenure is below `min_tenure_years`.** Status is `out_of_policy`. The comparison is `<`. The 90-day buffer does not open this. E205's laptop stops here. The same person's monitor has a minimum of 0, so it continues.
6. **Count is above `max_count`.** Status is `indeterminate`. The file already holds more units than the sheet allows. Issue dates are not read. E208 stops here.
7. **Count is under `max_count`.** Status is `in_policy`. The role still has room for another unit, so existing units do not have to be old yet. Issue dates are not required, and a blank date on this path does not escalate. E201's one monitor against a manager cap of 2 stops here. E207's headset against a standard cap of 1 also stops here.
8. **Count equals `max_count`.** This is a replacement. The due date is `issued_on` plus `refresh_years` calendar years. February 29 in a year that has no February 29 becomes February 28. Decide in this order:
   1. **Missing `issued_on`.** Any unit of this item has no issue date. Status is `indeterminate`. No due date is calculated. The seed data has no such unit.
   2. **Split history.** More than one unit, the oldest is already due, and the newest is not. Status is `indeterminate`. One unit cannot split, because the oldest and the newest are the same object. This runs before the buffer. E211 stops here.
   3. **Refresh is due.** The newest unit's due date is on or before 2026-10-01. Status is `in_policy`.
   4. **Early-request buffer.** The as-of date falls in the 90 days before the due date, and the due date is still after 2026-10-01. Status is `indeterminate`. The sheet says the period is not over. A person might still approve the request so the equipment is fulfilled as the next period starts. The server will not choose.
   5. **Too soon.** The due date is more than 90 days away. Status is `out_of_policy`.

A standard monitor issued on 2023-08-01 is due on 2026-08-01, which is already past, so a person at the cap is a clear approval. The same monitor issued on 2024-01-15 comes due on 2027-01-15. On 2026-10-01 that due date is 106 days away, which is outside the buffer, so it is a clear denial. Issued so that the due date falls inside the next 90 days, it escalates.

A tenure shortfall stays `out_of_policy`. The buffer does not open the standard laptop to someone in their first year.

| Situation | `within_policy` | `status` | Assistant |
|---|---|---|---|
| Under `max_count`, and tenure is at least `min_tenure_years` | `true` | `in_policy` | Approve. Do not escalate. |
| At `max_count`, the newest unit is already due, and the history is not split | `true` | `in_policy` | Approve. Do not escalate. |
| Known item, absent from this role's sheet | `false` | `out_of_policy` | Deny. Do not escalate. |
| At `max_count`, and the due date is more than 90 days away | `false` | `out_of_policy` | Deny. Do not escalate. |
| Tenure is below `min_tenure_years` | `false` | `out_of_policy` | Deny. Do not escalate. |
| At `max_count`, and a unit of that item has no issue date | `null` | `indeterminate` | Escalate. The seed data has no row like this. The function still refuses to invent a due date if one appears. |
| The item is not in the catalog, such as `keyboard` | `null` | `indeterminate` | Escalate. |
| The count on file is already above `max_count` | `null` | `indeterminate` | Escalate. |
| At `max_count`, the oldest unit is due, and the newest is not | `null` | `indeterminate` | Escalate. The reason names both issue dates. |
| At `max_count`, and the as-of date is inside the 90 days before the due date | `null` | `indeterminate` | Escalate. The reason says the refresh is not due and the request is inside the early-request buffer. |
| The employee exists, and their role has no sheet (`contractor`) | `null` | `indeterminate` | Escalate. |
| No employee with that id | `null` | `not_found` | Escalate, with a reason that the person is not on file. |

`in_policy` and `out_of_policy` are clear. The assistant writes the approval or the denial from the tool's `reason` and `facts`.

`indeterminate` means the server will not guess. A keyboard request, a count already over the cap, and a role with no sheet are cases the stored records can produce. A missing issue date is not one of those records. Every seeded unit has a date, because a write would have required one. If a unit at the cap has no date anyway, eligibility still returns `indeterminate` instead of inventing a due date. The split history and the 90-day buffer are different from all of these. Those dates are complete, and they still do not pick a side. `not_found` is also not a denial. Denying a person who is not on file would be a guess. All of these are successful tool results. `within_policy` is `null`, and the assistant escalates.

A call that omits an argument, or sends a number where a string is required, fails in the tool schema before eligibility runs. That failure is not one of the statuses above.

The mock data is able to produce every row of this table.

## Escalation

`flag_for_human_review` files a ticket in the server. The ticket list lives in the server process. The assistant does not keep that list. IT would read it from the server. The list is in memory, so it clears when the process stops. Tests can clear it between cases. The tool does not email anyone or open an external queue.

The assistant calls it only for `indeterminate` and `not_found`. It does not call it for a clear approval or a clear denial. An early request inside the 90-day buffer and a split equipment history are both `indeterminate`, so both are filed here, each with its own reason.

Each call appends one ticket, including when the employee id is not on file, and returns a copy of that ticket with a new id (`ESC-1`, `ESC-2`, and so on). The id counts tickets currently stored. After the list is cleared, the next id is `ESC-1` again. `request` is the original request text. `reason` is a required string: why it was escalated, taken from the eligibility `reason`. The tool does not accept a null reason, and it does not decide whether the case should be flagged. A second call creates a second ticket. `reset_escalations` clears the list and is not an MCP tool.

## Tool schemas

Values below are the shapes the tools return. Names match the parameters.

### `get_employee_info(employee_id)`

Looks up the person. Returns role, tenure, and the equipment on file.

Input:

```json
{ "employee_id": "E202" }
```

Found:

```json
{
  "employee_id": "E202",
  "role": "standard",
  "tenure_years": 8.6,
  "equipment": [
    { "item": "monitor", "issued_on": "2023-08-01" }
  ]
}
```

Missing id:

```json
{ "employee_id": "E999", "status": "not_found" }
```

### `get_policy_limits(role)`

Returns the sheet for one role: each item that role may request, and how often. It does not look at a person, and it does not drop rows because of someone's tenure.

Input:

```json
{ "role": "standard" }
```

Found:

```json
{
  "role": "standard",
  "items": [
    { "item": "monitor", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0 },
    { "item": "laptop", "max_count": 1, "refresh_years": 4, "min_tenure_years": 1 }
  ]
}
```

A manager sheet also includes dock. A director sheet includes dock with that role's numbers. A standard sheet has no dock row.

Unknown role, including `contractor`:

```json
{ "role": "contractor", "status": "not_found" }
```

### `check_request_eligibility(employee_id, item)`

Returns whether this person and this item fall inside policy, plus the status the assistant must follow.

Input:

```json
{ "employee_id": "E202", "item": "monitor" }
```

In policy. This is E202, at the cap, with a monitor whose refresh is already due. The `reason` is the sentence for that outcome. The role in the sentence is capitalized. The role in `facts` is the stored value.

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

Outside policy uses the same fields with `within_policy` false and `status` `out_of_policy`.

Indeterminate and not-found use `within_policy` null, `status` `indeterminate` or `not_found`, a `reason`, and whatever `facts` were actually known. A missing employee has no role, tenure, or equipment facts. Each outcome has one sentence. Those sentences are listed in `docs/server.md`.

### `flag_for_human_review(employee_id, request, reason)`

Appends a ticket and returns the stored copy.

Input:

```json
{
  "employee_id": "E207",
  "request": "I need a keyboard.",
  "reason": "Item 'keyboard' is not in the catalog."
}
```

Output:

```json
{
  "escalation_id": "ESC-1",
  "employee_id": "E207",
  "request": "I need a keyboard.",
  "reason": "Item 'keyboard' is not in the catalog."
}
```

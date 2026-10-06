# Corpus coverage

The mock data is built so each eligibility rule has its own record. The as-of date is **2026-10-01**. A standard employee may hold one monitor, refreshed every 3 years. A manager may hold two. Asking for a different item on the same person can be a different case.

The tool `reason` for each case is the outcome sentence in `docs/server.md`. The notes below say why the case lands on that outcome.

Dates are fixed. The suite does not use the calendar day you run it.

## Clear approval

| Employee | Request | Why it is in policy |
|---|---|---|
| E201, manager, one monitor issued 2025-01-01 | monitor | The monitor is new. The cap is 2, so this is another unit, not a replacement. |
| E202, standard, one monitor issued 2023-08-01 | monitor | Already at the cap of 1. The due date 2026-08-01 is in the past, so the refresh is due. |
| E205, hired 2026-04-01, tenure 0.5, no equipment | monitor | Count is 0 and the monitor rule has no tenure gate. |
| E207, standard, no equipment | headset | Count is 0 and headset is on the standard sheet. |

## Clear denial

| Employee | Request | Why it is out of policy |
|---|---|---|
| E203, standard, one monitor issued 2024-01-15 | monitor | Due date 2027-01-15 is 106 days away, outside the 90-day buffer. |
| E204, standard, no equipment | dock | Dock is a catalog item and is not on the standard sheet. |
| E205, tenure 0.5 | laptop | A standard laptop requires 1 year. The same person is approved for a monitor. |

## Escalate: the dates are complete and still do not decide

| Employee | Request | Why it is indeterminate |
|---|---|---|
| E210, standard, one monitor issued 2023-11-15 | monitor | Due date 2026-11-15 is 45 days away, inside the 90-day early-request buffer. |
| E211, manager, monitors issued 2020-06-01 and 2026-06-01 | monitor | Count equals the cap of 2. The 2020 unit is already due. The 2026 unit is not. |

## Escalate: the request or the rules do not apply

Every seeded unit has an issue date. A blank date is not a person in this set. If a unit at the cap has no date anyway, eligibility still escalates instead of inventing a due date. The test for that guard inserts a temporary row and deletes it.

| Employee | Request | Why it is indeterminate |
|---|---|---|
| E207, standard, no equipment | keyboard | Keyboard is not in the catalog. |
| E208, standard, two dated monitors | monitor | Cap is 1, so two units is already over the max. |
| E209, role contractor, one monitor on file | monitor | The person exists. Contractor has no policy sheet. |

`get_policy_limits("contractor")` is `not_found`. That is a different result from E209's eligibility call. E209 is not in the live host query set (`docs/host-queries.md`).

## Lookup only

**E212**, director, no equipment, tenure 10.4. This record exists so a director can be returned by `get_employee_info` and the director sheet can be returned by `get_policy_limits`. No eligibility case depends on this person.

**E999** is not in the file. An employee lookup and a monitor request for that id are both `not_found`. A keyboard request for E999 stays `not_found`. The missing person is decided before the unknown item.

## Pairs that look alike and are not

| Pair | What changes | Results |
|---|---|---|
| E203 and E210 | How far the due date is from 2026-10-01 | 106 days is a denial. 45 days is the early-request buffer. |
| E208 and E211 | Count against the cap | Two monitors on a standard employee is over the cap. Two monitors on a manager is a split history at the cap. |
| E204 and E207 | The item, not the empty equipment list | Dock is a known item missing from the standard sheet, so it is a denial. Keyboard is not in the catalog, so it is indeterminate. E207 headset is an approval. |
| E205, two requests | The item's tenure gate | Monitor is approved. Laptop is denied. |
| E201 and E203 | Under the cap versus at the cap | E201's new monitor is still an approval because the manager cap is 2. E203 is at the cap and too early, so it is a denial. |

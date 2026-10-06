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


| Employee | Request | Why it is indeterminate |
|---|---|---|
| E207, standard, no equipment | keyboard | Keyboard is not in the catalog. |
| E208, standard, two dated monitors | monitor | Cap is 1, so two units is already over the max. |


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
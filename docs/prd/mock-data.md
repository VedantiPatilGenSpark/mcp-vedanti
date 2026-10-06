# PRD: mock data corpus

`src/mcp_vedanti/data.py` holds these records and does not decide eligibility. Do not invent extra employees or change a date.

The rules live in `docs/prd/requirements.md`. `docs/prd/tests.md` asserts these same ids and outcomes.

## File

`src/mcp_vedanti/data.py` exports:

| Name | Value |
|---|---|
| `AS_OF` | `datetime.date(2026, 10, 1)` |
| `EARLY_REQUEST_DAYS` | `90` |
| `CATALOG_ITEMS` | `("monitor", "laptop", "dock", "headset")` |
| `POLICY_ROLES` | `("standard", "manager", "director")` |
| `POLICY` | the three sheets below |
| `EMPLOYEES` | the records below, keyed by `employee_id` |

`keyboard` is not a catalog item. `contractor` is not a policy role. Do not add a sheet for it.

No function in this file decides eligibility, computes tenure, or files an escalation. Dates are stored as ISO strings. Callers do the math.

## Policy sheets

Each item rule is `max_count`, `refresh_years`, `min_tenure_years`.

**standard:** monitor `1 / 3 / 0`, laptop `1 / 4 / 1`, headset `1 / 3 / 0`. No dock row.

**manager:** monitor `2 / 3 / 0`, laptop `1 / 2 / 0`, dock `1 / 4 / 0`, headset `1 / 3 / 0`.

**director:** monitor `2 / 2 / 0`, laptop `1 / 2 / 0`, dock `1 / 3 / 0`, headset `1 / 3 / 0`.

Store items in that order. Role and item strings are already lowercase.

## Employees

Tenure below is what `get_employee_info` must later return for `AS_OF`. It is listed here so the other briefs share one number. Do not store `tenure_years` on the record. Store `hire_date` only.

Equipment is one object per unit: `{"item": "...", "issued_on": "YYYY-MM-DD"}`. Every stored issue date is a real date. The seed data does not contain a blank `issued_on`.

| Id | Role | Hire date | Tenure years | Equipment | Why this record exists |
|---|---|---|---|---|---|
| E201 | manager | 2019-06-01 | 7.3 | one monitor, 2025-01-01 | One monitor is under the manager cap of 2. |
| E202 | standard | 2018-03-01 | 8.6 | one monitor, 2023-08-01 | Due date 2026-08-01 is already past. Cap is 1. |
| E203 | standard | 2018-03-01 | 8.6 | one monitor, 2024-01-15 | Due date 2027-01-15 is 106 days after the as-of date. |
| E204 | standard | 2018-03-01 | 8.6 | none | Dock is a catalog item and is not on the standard sheet. |
| E205 | standard | 2026-04-01 | 0.5 | none | Tenure is under the standard laptop gate of 1 year. Monitor has no tenure gate. |
| E207 | standard | 2018-03-01 | 8.6 | none | Used with item `headset` (on the standard sheet, under the cap) and with item `keyboard` (not in the catalog). |
| E208 | standard | 2018-03-01 | 8.6 | monitors issued 2020-01-01 and 2021-06-01 | Two monitors is already over the standard cap of 1. Both dates are present. |
| E209 | contractor | 2018-03-01 | 8.6 | one monitor, 2022-01-15 | The person is on file. The role has no sheet. |
| E210 | standard | 2018-03-01 | 8.6 | one monitor, 2023-11-15 | Due date 2026-11-15 is 45 days after the as-of date, inside the 90-day buffer. Cap is 1. |
| E211 | manager | 2015-01-01 | 11.7 | monitors issued 2020-06-01 and 2026-06-01 | Cap is 2. The 2020 unit is due. The 2026 unit is not. |
| E212 | director | 2016-05-01 | 10.4 | none | A director exists so the third role can be looked up. |

There is no employee `E999`. That id is the missing-employee case, and it must stay absent.

## Done when

`data.py` exports the names above, the three sheets match the table, and the eleven employees match the rows. The file contains no decision logic. That is the file as it stands.

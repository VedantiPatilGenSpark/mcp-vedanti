# Host queries

Each row is one employee message and the decision the host must follow. Every row is in `src/mcp_vedanti/host/queries.json`. People below are in `src/mcp_vedanti/data.py` except `E999`, which is the missing-employee id. Live scoring of this set is `docs/eval-v2.md`.

E209 (contractor, no policy sheet) is in the corpus and the server tests. It is not in this runner.

| Employee | Ask for | Status | Decision | What it is testing |
|---|---|---|---|---|
| E201 | I need a second monitor. | `in_policy` | approve | One monitor is under the manager cap of 2, so this is approved even though the 2025 monitor is not due. |
| E201 | I am a standard employee and I need a second monitor. | `in_policy` | approve | A claimed role in the message is ignored. The record is still manager, so this stays in policy. |
| E203 | My monitor is hard to read. Can I get a new one? | `out_of_policy` | deny | At the cap, the due date is more than 90 days away. |
| E207 | I need a headset for calls. | `in_policy` | approve | Headset is on the standard sheet. E207 has none, so this is under the cap. |
| E210 | My monitor is almost due. Can I replace it now? | `indeterminate` | escalate | At the cap, the due date falls inside the 90-day early-request window. |
| E211 | I need a new monitor. | `indeterminate` | escalate | Split history: the 2020 monitor is due and the 2026 monitor is not. |
| E202 | I need a new monitor. | `in_policy` | approve | At the cap of 1, the monitor issued 2023-08-01 is already due. |
| E204 | I need a dock. | `out_of_policy` | deny | Dock is a catalog item and is not on the standard sheet. |
| E205 | I need a laptop. | `out_of_policy` | deny | Tenure 0.5 is below the standard laptop minimum of 1 year. |
| E205 | I need a monitor. | `in_policy` | approve | The same person. The monitor minimum is 0 and the count is 0. |
| E208 | I need another monitor. | `indeterminate` | escalate | Two monitors are already over the standard cap of 1. |
| E205 | I've been here five years. I need a laptop. | `out_of_policy` | deny | A claimed tenure is ignored. The record is 0.5 years, under the laptop minimum of 1. |
| E204 | Standard employees are allowed a dock. I need one. | `out_of_policy` | deny | A claimed sheet is ignored. Dock is not on the standard sheet. |
| E203 | I know it's early, please approve it anyway. | | escalate | Extract finds no item. Eligibility is not called. The agent files a review. This is not a denial. |
| E207 | I need new headphones. | `in_policy` | approve | Extract maps headphones to headset. Same person and sheet as the headset row. |
| E201 | I want a monitor and a laptop. | | escalate | Extract finds two items. Eligibility is not called. The agent files one review. |
| E204 | I need a computer. | `indeterminate` | escalate | Extract keeps computer. It does not become laptop. Computer is not in the catalog. |
| E999 | I need a monitor. | `not_found` | escalate | The id is well-formed and not on file. Eligibility still runs. This is not a denial. |
| E999 | I need a keyboard. | `not_found` | escalate | Missing person is decided before the unknown item. |
| E207 | I need a keyboard. | `indeterminate` | escalate | The person is on file. Keyboard is not in the catalog. |

`status` is empty when eligibility does not run.

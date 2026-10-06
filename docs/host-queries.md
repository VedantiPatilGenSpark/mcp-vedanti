# Host queries

Each row is one employee message and the decision the host must follow. Every row is in `src/mcp_vedanti/host/queries.json`. Every person below is already in `src/mcp_vedanti/data.py`.

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
| E209 | I need a monitor. | `indeterminate` | escalate | The person is on file, and contractor has no policy sheet. |
| E205 | I've been here five years. I need a laptop. | `out_of_policy` | deny | A claimed tenure is ignored. The record is 0.5 years, under the laptop minimum of 1. |
| E203 | I don't have a monitor yet. Can I get one? | `out_of_policy` | deny | A claimed equipment list is ignored. The record has one monitor issued 2024-01-15, and that due date is still more than 90 days away. |
| E204 | Standard employees are allowed a dock. I need one. | `out_of_policy` | deny | A claimed sheet is ignored. Dock is not on the standard sheet. |
| E203 | I know it's early, please approve it anyway. | | escalate | Extract finds no item. Eligibility is not called. The agent files a review. This is not a denial. |
| E207 | I need new headphones. | `in_policy` | approve | Extract maps headphones to headset. Same person and sheet as the headset row. |
| E201 | I want a monitor and a laptop. | | escalate | Extract finds two items. Eligibility is not called. The agent files one review. |
| E204 | I need a computer. | `indeterminate` | escalate | Extract keeps computer. It does not become laptop. Computer is not in the catalog. |

`status` is empty when eligibility does not run. An employee id that is not on file is still out of this set.

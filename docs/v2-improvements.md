# Left for a later query-set pass

No-item, two-item, headphones, and computer rows are in `src/mcp_vedanti/host/queries.json` and `docs/host-queries.md`.

Still not in the query set: an employee id that is not on file.

Examples: E999, "I need a monitor." E999, "I need a keyboard."

`E999` is not in the employee file. `get_employee_info` returns `status: not_found`. That field is the lookup result. It is not the classification.

The host still checks eligibility with that employee id and the item named in the message. Eligibility returns `not_found`, including when the item is a keyboard. The missing person is decided before the unknown item. The reason is that no employee with that id is on file.

The host then files a human review. `request` is the original message. `reason` is that eligibility sentence. The draft says the request was escalated. This is not a denial.

Server tests for E999 stay. This file can be deleted once those rows are in the query set.

# Host requirements

How the chat host uses the equipment server. The server rules stay in `requirements.md`. This file records host decisions as they are made.

## CLI input

The CLI asks for two fields, `employee_id` and `query`. Both must be non-empty strings. The CLI asks again until each one has text. An empty string does not start the agent, does not call a tool, and does not file a ticket.

The CLI does not check that the id is on file. A non-empty id that the server does not know is a normal `not_found` result. `query` is the request text. The agent reads the item from that query. The employee does not type the item as its own field.

After both fields are non-empty, the agent runs once and the CLI prints one reply. The agent does not ask a follow-up question.

## Tool results the host must tell apart

The host reads the tool result before it drafts a reply.

| What came back | What it is |
|---|---|
| A result with `status` | The server classified the case. `in_policy`, `out_of_policy`, `indeterminate`, and `not_found` are all successful tool results. |
| `isError: true` on `tools/call` | The SDK rejected the arguments before the function ran. The result has no `status`. |
| No tool result | The server never answered. The HTTP call failed, returned a 5xx, or the connection dropped. |

## A bad call

A missing argument, or a number where a string is required, is a bad call the host made. The server is up. The equipment function does not run.

The employee does not see this error. The agent does not see it either. The harness is the code that performs the tool call. It intercepts `isError` before that result is appended to the agent transcript. The agent does not repair the call, and it does not escalate, approve, or deny from the error text.

A string that arrived as a number is sent again as a string. That retry is one call, made by the harness, and it is not shown to the agent. The harness does not send the same invalid payload again.

`employee_id` and `query` are already non-empty before this path. The harness does not ask the agent to question the employee. The raw SDK error stays out of the transcript and out of the reply.

A second `isError` after the corrected call is logged with the tool name and the error text. The harness stops. It does not keep retrying, and it still does not show the tool error to the agent or the employee.

## What the employee sees

A classified result has one of three replies.

| `status` | Reply | Ticket |
|---|---|---|
| `in_policy` | An approval written from `reason` and `facts`. | Do not call `flag_for_human_review`. |
| `out_of_policy` | A denial written from `reason` and `facts`. | Do not call `flag_for_human_review`. |
| `indeterminate` or `not_found` | One shared escalation sentence. The employee does not see a different sentence for a missing id, an unknown item, a split history, or the 90-day buffer. | Call `flag_for_human_review`. The ticket stores the specific eligibility `reason`. The shared sentence is only the reply. |

An id that is not on file is `not_found`. It uses that same escalation sentence.

A bad call and a server that never answers are not classified results. They do not use the escalation sentence, and they do not file a ticket.

## The server never answers

A 5xx or a dropped connection means no tool result came back. There is no `status` and no `isError` body to read.

The host does not invent an eligibility status and does not call `flag_for_human_review`. The employee sees that the equipment system could not be reached and that they can try again later.

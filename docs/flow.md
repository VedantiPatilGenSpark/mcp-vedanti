# Request flow

End-to-end path of one employee id and query. The server classifies. The host talks to the employee and follows that class.

## Host pipeline

```mermaid
flowchart TD
  start[Employee ID + Query] --> idShape{Id is E plus 3 digits?}
  idShape -->|no| idHint[Re-prompt: format Exxx]
  idHint --> start
  idShape -->|yes| normalize[Normalize to E###]
  normalize --> extract[Extract item: one LLM call]

  extract --> item{Item}
  item -->|one name| bound["ReAct user: Item: monitor"]
  item -->|none, two-plus, or bad JSON| nullItem["ReAct user: Item: null"]

  bound --> catalog[list_tools]
  nullItem --> catalog
  catalog --> react[ReAct loop: up to 8 JSON steps]

  react --> step{Model JSON}
  step -->|not tool or draft| observeParse[Observation: unusable reply]
  observeParse --> react
  step -->|tool| guards{Host guards}
  guards -->|blocked| observeGuard[Observation: why the call is illegal]
  observeGuard --> react
  guards -->|allowed| mcp[MCP tool on :8000]
  mcp --> observe[Observation: tool result]
  observe --> react
  step -->|draft, path not done| observeEarly[Observation: eligibility or ticket still due]
  observeEarly --> react
  step -->|draft, path done| reflect[Reflector: confirm or rewrite wording]
  reflect --> reply[Employee reply]
  react -->|8 steps, no finish| stepLimit[Sorry, could not finish. No ticket invented.]
```

## Named item vs null item

```mermaid
flowchart TD
  item{Item in ReAct user message}
  item -->|null| flagNull[flag for human review]
  flagNull --> draftEsc[Draft: escalated]
  item -->|one name| lookup[get_employee_info]

  lookup --> found{Person on file?}
  found -->|no| eligMissing[check_request_eligibility]
  eligMissing --> notFound[status not_found]
  notFound --> flagReview[flag for human review]
  flagReview --> draftEsc

  found -->|yes| policy[get_policy_limits for that role]
  policy --> elig[check_request_eligibility]
  elig --> status{status}
  status -->|in_policy| approve[Draft: approve. No ticket.]
  status -->|out_of_policy| deny[Draft: deny. No ticket.]
  status -->|indeterminate or not_found| flagReview
```

The model still chooses each tool. The host blocks the wrong order: no eligibility before lookup, no eligibility before the role’s sheet when the person was found, no eligibility when `Item` is `null`, no ticket on approve or deny, no ticket on a bound item until eligibility has a status.

## What eligibility returns

```mermaid
flowchart TD
  elig[check_request_eligibility] --> s1{Employee on file?}
  s1 -->|no| nf[not_found: escalate]
  s1 -->|yes| s2{Role has a sheet?}
  s2 -->|no| ind1[indeterminate: escalate]
  s2 -->|yes| s3{Item in catalog?}
  s3 -->|no| ind2[indeterminate: escalate]
  s3 -->|yes| s4{Item on this sheet?}
  s4 -->|no| oop1[out_of_policy: deny]
  s4 -->|yes| s5{Tenure at least minimum?}
  s5 -->|no| oop2[out_of_policy: deny]
  s5 -->|yes| s6{Count vs max}
  s6 -->|above max| ind3[indeterminate: escalate]
  s6 -->|under max| in1[in_policy: approve]
  s6 -->|at max| s7{Refresh}
  s7 -->|split or missing date or 90-day buffer| ind4[indeterminate: escalate]
  s7 -->|due| in2[in_policy: approve]
  s7 -->|too soon| oop3[out_of_policy: deny]
```

Policy lookup and eligibility both read the same `_policy_sheet`. Facts never come from the query. A claimed role, tenure, or sheet is ignored.

## After a legal draft

The reflector sees observations and the draft, not the agent’s thoughts. It may confirm the draft or rewrite the wording. It must not change approve / deny / escalate.

`--queries --check` scores the class (`status` + decision) against `queries.json`. It does not score prose. Traces go to `runs/` or `--run-dir`.

# One-liner defenses

Scratch list for a later talk. Not a spec.

- Eligibility is the only classifier, and we skip it only when it cannot be called. A missing person with one item still can, so we take that `not_found` reason from eligibility, not from lookup.
- Lookup `not_found` is “this id is not in the dict.” It has no `reason`. Eligibility still runs so the ticket and the reply use one sentence: no employee is on file.
- Policy needs a role. Skip the sheet when lookup has no role. Do not skip eligibility.
- One extract call is cheaper than eight ReAct steps that time out on “please approve it anyway,” two items, or a synonym.
- Extract is language, not a system of record. It is not an MCP tool. After one name is bound, the model still chooses tools. That is the demo.
- The host does not flag before ReAct. `flag_for_human_review` is one of the four jobs. The agent files the ticket so `list_tools` is not ornamental.
- ReAct always sees `Item`. A name is bound. Zero items or two-plus items are `null`. The model should not have to infer that the field was omitted.
- Two named items escalate once. We do not loop per item.
- `status` is what eligibility returned, or `None`. We do not invent a fifth classification when eligibility never ran.
- The four tools are four jobs. Eligibility re-reads the person and the sheet so the host cannot forge a role.
- Policy lookup and eligibility share `_policy_sheet`, so they cannot drift onto different copies of `POLICY`.
- A malformed id is a CLI format error. A well-formed id missing from the file is escalate, the same as stale HR data.
- Facts come from tools. A claimed role, tenure, equipment list, or policy in the query does not override the record.
- `headphones` may become `headset`. `computer` is not a laptop. Same-device language is extract. A different device stays unknown until eligibility.
- Headset is on the sheets. Keyboard is not in the catalog. Unknown catalog is escalate, not deny.
- The ReAct prompt names jobs in English. Snake-case tool names come from `list_tools`. The host must not own the API surface twice.
- Sequence lives in the harness: lookup, then the role’s sheet if the person was found, then eligibility. A branched “if on file…” prompt caused draft-after-lookup loops.
- Employee-facing draft essays were dropped. They pulled a draft before the ticket and plain text after it. Class is scored; prose is not.
- Live `--queries --check` compares `status` and `decision` only. A step limit is a fail. Draft wording is not a golden.
- The step-limit reply does not invent a ticket. We did not finish the request.
- E209 contractor stays in the corpus and the server tests. It is not in the live query set. The person-on-file / no-sheet rule is still tested without a ReAct row the model could not finish.

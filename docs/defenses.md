# One-liner defenses

Scratch list for a later talk. Not a spec.

- Eligibility is the only classifier, and we skip it only when it cannot be called. A missing person with one item still can, so we take that `not_found` reason from eligibility, not from lookup.
- One extract call is cheaper than eight ReAct steps that time out on “please approve it anyway,” two items, or a synonym.
- `status` is what eligibility returned, or `None`. We do not invent a fifth classification when eligibility never ran.
- The four tools are four jobs. Eligibility re-reads the person and the sheet so the host cannot forge a role.
- A malformed id is a CLI format error. A well-formed id missing from the file is escalate, the same as stale HR data.

# mcp-vedanti

An IT equipment-request lab. One program classifies a request. A second program talks to an employee and follows that classification.

The server is an MCP service. It looks up an employee, reads that role's policy, and classifies one item. The host is a separate program. It never imports the server code. It calls the server over HTTP. A local model names the item, then chooses which tool to call next.

## How a request is decided

The employee id comes from a prompt or from `--employee-id`. It must look like `E201` (letter `E` and three digits, any case). The host capitalizes it. A well-formed id that is not on file is not a CLI error. Eligibility returns `not_found` and the host escalates.

The item is named in one model call before ReAct. Same-device words may become the catalog word (`headphones` → `headset`). A different device is not rewritten (`computer` is not `laptop`). If extract finds no item, or two or more, the agent files a review and eligibility is not called. `status` in the query set is empty for those rows.

When there is one item, the server returns one status, and the host follows it.

| Status | What the host does |
|---|---|
| `in_policy` | Approve. No ticket. |
| `out_of_policy` | Deny. No ticket. |
| `indeterminate` | File a human review, then say the request was escalated. |
| `not_found` | File a human review, then say the request was escalated. This is not a denial. |

A claimed role, tenure, equipment list, or policy in the message does not change the record. When eligibility ran, the server's `reason` is the sentence the reply is written from.

## Layout

```text
src/mcp_vedanti/server.py        MCP server. Registers the four tools.
src/mcp_vedanti/equipment.py     Lookup, policy, eligibility, and tickets.
src/mcp_vedanti/data.py          Synthetic employees and policy sheets.
src/mcp_vedanti/host/            Host. Model, MCP client, extract, and request loop.
src/mcp_vedanti/host/queries.json
                                 Saved requests and the expected decision.
tests/                           Server tests and host tests. No model required.
docs/prd/                     Server requirements, mock data, and test contract.
docs/host-queries.md             What each saved request is checking.
```

The host first asks the model to name the item. Then the ReAct loop asks for one JSON step at a time: a tool call, or a draft reply. Python runs the tool and appends the observation. It blocks a skip of lookup or policy, and a tool argument that changes the bound id or item. After a draft is allowed, a second model call checks the wording. The run file ends with `Verdict:` (`confirm` or `rewrite`) and `Reply:`.

## Requirements

- Python 3.12
- [Ollama](https://ollama.com) with `qwen3:8b`, only for a live host run
- The equipment server listening on port 8000 before the host starts

Tests do not need Ollama or a running server.

## Setup

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

`pip install -e .` is required. Without it, `python -m mcp_vedanti` cannot find the package.

Pull the model once:

```bash
ollama pull qwen3:8b
```

## Run the server

In one terminal:

```bash
python -m mcp_vedanti
```

This serves the MCP endpoint at `http://127.0.0.1:8000/mcp`. Leave it running. The four tools are `get_employee_info`, `get_policy_limits`, `check_request_eligibility`, and `flag_for_human_review`.

## Run the host

In a second terminal, with the same virtualenv:

```bash
python -m mcp_vedanti.host
```

The host prompts `Employee ID: ` and `Query: ` until each line is non-empty. A bad id shape prints `Employee ID must look like E201.` and asks again. `e201` is stored as `E201`.

Flags still work:

```bash
python -m mcp_vedanti.host --employee-id e201 --query "I need a second monitor."
```

To run every saved request, with no prompts:

```bash
python -m mcp_vedanti.host --queries
```

`--queries` cannot be mixed with `--employee-id` or `--query`.

Each request is printed as it happens and written to `runs/`. That directory is gitignored. A finished file looks like this:

```text
Thought: ...
Action: check_request_eligibility {"employee_id": "E201", "item": "monitor"}
Observation: { ... "status": "in_policy" ... }
Draft: ...
Verdict: confirm
Reply: ...
```

The model is set in `src/mcp_vedanti/host/config.json`: `qwen3:8b`, thinking off, temperature 0. Inside the dev container the Ollama URL is `http://host.docker.internal:11434`. On the machine where Ollama is running, change `base_url` to `http://127.0.0.1:11434`.

## Tests

```bash
pytest
```

The host tests use a scripted model. They do not call Ollama or the live server.

## Dev container

Docker Desktop has to be running. Open this folder in Cursor, then run **Dev Containers: Reopen in Container**. The workspace inside the container is `/workspaces/MCP_Vedanti`.

The container installs Python 3.12 and the requirements. It does not install this package. After the container is up, run `pip install -e .` once, then use the same server and host commands above.

## Read next

- `docs/prd/requirements.md` — eligibility rules and the four statuses
- `docs/server.md` — the check order and the reason sentences
- `docs/corpus.md` — why each employee record is in the mock data
- `docs/host-queries.md` — each saved request and why it approves, denies, or escalates
- `docs/extract-prelude.md` — why item extract runs before ReAct
- `docs/defenses.md` — one-liner design notes

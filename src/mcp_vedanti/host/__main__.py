"""Run one equipment request, or the saved query set."""

import argparse
import asyncio
import json
import re
from pathlib import Path

from mcp_vedanti.host.adapter import load_adapter
from mcp_vedanti.host.loop import run_request

QUERIES_PATH = Path(__file__).with_name("queries.json")

_EMPLOYEE_ID = re.compile(r"^e\d{3}$", re.IGNORECASE)
_ID_HINT = "Invalid Employee ID. Please enter Employee ID in format Exxx."


def normalize_employee_id(value: str) -> str | None:
    """Return E plus three digits, or None when the value is not that shape."""
    stripped = value.strip()
    if _EMPLOYEE_ID.fullmatch(stripped) is None:
        return None
    return "E" + stripped[1:]


def prompt_employee_id(*, input_fn=None, print_fn=None) -> str:
    """Ask for an employee id until the line is a valid E plus three digits."""
    if input_fn is None:
        input_fn = input
    if print_fn is None:
        print_fn = print
    while True:
        raw = input_fn("Employee ID: ")
        normalized = normalize_employee_id(raw)
        if normalized is not None:
            return normalized
        if raw.strip():
            print_fn(_ID_HINT)


def prompt_query(*, input_fn=None) -> str:
    """Ask for the employee request until the line is not empty."""
    if input_fn is None:
        input_fn = input
    while True:
        query = input_fn("Query: ").strip()
        if query:
            return query


def main() -> None:
    """Run one request, or every saved query, through the host loop."""
    parser = argparse.ArgumentParser(
        prog="python -m mcp_vedanti.host",
        description="Run an equipment request.",
    )
    parser.add_argument("--employee-id", help="Employee id for one request.")
    parser.add_argument("--query", help="The employee's words for one request.")
    parser.add_argument(
        "--queries",
        action="store_true",
        help="Run every saved query.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="With --queries, compare each run's status and decision to queries.json.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="Directory for run files. Default is runs/.",
    )
    args = parser.parse_args()
    run_dir = args.run_dir
    if args.check and not args.queries:
        parser.error("--check is only valid with --queries.")
    if args.queries:
        if args.employee_id or args.query:
            parser.error("Pass --queries by itself.")
        asyncio.run(_saved(run_dir=run_dir, check=args.check))
        return
    employee_id = _flag_employee_id(parser, args.employee_id)
    if employee_id is None:
        employee_id = prompt_employee_id()
    query = args.query.strip() if args.query else ""
    if not query:
        query = prompt_query()
    asyncio.run(run_request(employee_id, query, load_adapter(), run_dir=run_dir))


def _flag_employee_id(parser: argparse.ArgumentParser, value: str | None) -> str | None:
    """Normalize a flag id, or error when the flag is present and malformed."""
    if not value:
        return None
    normalized = normalize_employee_id(value)
    if normalized is None:
        parser.error(_ID_HINT)
    return normalized


async def _saved(*, run_dir: Path | None, check: bool = False) -> None:
    """Run each saved row through the same path as one request."""
    rows = json.loads(QUERIES_PATH.read_text())
    adapter = load_adapter()
    kwargs = {}
    if run_dir is not None:
        kwargs["run_dir"] = run_dir
    failures = 0
    for row in rows:
        employee_id = normalize_employee_id(row["employee_id"]) or row["employee_id"]
        print(f"\n=== {employee_id}: {row['query']} ===", flush=True)
        result = await run_request(employee_id, row["query"], adapter, **kwargs)
        if not check:
            continue
        mismatch = _golden_mismatch(row, result)
        if mismatch is None:
            continue
        failures += 1
        print(f"CHECK FAIL {employee_id}: {row['query']}\n  {mismatch}", flush=True)
    if check and failures:
        print(f"\n{failures} of {len(rows)} queries failed the golden check.", flush=True)
        raise SystemExit(1)


def _golden_mismatch(row: dict, result: dict) -> str | None:
    """Why a run missed the saved status and decision, or None when it matched."""
    if result.get("stop") == "step_limit":
        return "stop=step_limit"
    expected_status = row.get("status")
    expected_decision = row.get("decision")
    got_status = result.get("status")
    got_decision = result.get("decision")
    if got_status == expected_status and got_decision == expected_decision:
        return None
    return (
        f"expected status={expected_status!r} decision={expected_decision!r} "
        f"got status={got_status!r} decision={got_decision!r}"
    )


if __name__ == "__main__":
    main()

"""Run one equipment request, or the saved query set."""

import argparse
import asyncio
import json
from pathlib import Path

from mcp_vedanti.host.adapter import load_adapter
from mcp_vedanti.host.loop import run_request

QUERIES_PATH = Path(__file__).with_name("queries.json")


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
    args = parser.parse_args()
    if args.queries:
        if args.employee_id or args.query:
            parser.error("Pass --queries by itself.")
        asyncio.run(_saved())
        return
    if not args.employee_id or not args.query:
        parser.error("Pass --employee-id and --query, or pass --queries.")
    asyncio.run(run_request(args.employee_id, args.query, load_adapter()))


async def _saved() -> None:
    """Run each saved row through the same path as one request."""
    rows = json.loads(QUERIES_PATH.read_text())
    adapter = load_adapter()
    for row in rows:
        print(f"\n=== {row['employee_id']}: {row['query']} ===", flush=True)
        await run_request(row["employee_id"], row["query"], adapter)


if __name__ == "__main__":
    main()

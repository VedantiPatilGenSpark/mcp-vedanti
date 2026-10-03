"""Print a request trace and write the same text to one file."""

import json
import re
from pathlib import Path

RUNS_DIR = Path("runs")


def format_event(event: dict) -> str:
    """One trace event as a single block of text."""
    kind = event["kind"]
    if kind == "thought":
        return f"Thought: {event['text']}"
    if kind == "action":
        arguments = json.dumps(event["arguments"], ensure_ascii=False)
        return f"Action: {event['tool']} {arguments}"
    if kind == "observation":
        return f"Observation: {event['text']}"
    if kind == "draft":
        return f"Draft: {event['text']}"
    raise ValueError(f"Unknown trace event: {kind}")


def format_run(
    trace: list[dict],
    *,
    verdict: str | None = None,
    reply: str | None = None,
) -> str:
    """The trace, then the reflector verdict and employee reply when they exist."""
    parts = [format_event(event) for event in trace]
    if verdict is not None:
        parts.append(f"Verdict: {verdict}")
    if reply is not None:
        parts.append(f"Reply: {reply}")
    return "\n".join(parts) + "\n"


def run_path(directory: Path, employee_id: str, query: str) -> Path:
    """One file name per employee and query text."""
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:48]
    return directory / f"{employee_id}-{slug}.txt"


def write_run(path: Path, text: str) -> None:
    """Create the parent directory and write the run text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

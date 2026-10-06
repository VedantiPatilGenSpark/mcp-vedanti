"""Confirm host CLI prompts, id format, and normalization. No Ollama or server."""

import asyncio
import sys

import pytest

from mcp_vedanti.host.__main__ import (
    _golden_mismatch,
    main,
    normalize_employee_id,
    prompt_employee_id,
    prompt_query,
)


def test_normalize_accepts_e_and_three_digits() -> None:
    """E201 stays E201."""
    assert normalize_employee_id("E201") == "E201"


def test_normalize_is_case_insensitive() -> None:
    """e201 becomes E201."""
    assert normalize_employee_id("e201") == "E201"


def test_normalize_strips_whitespace() -> None:
    """Surrounding space is ignored before the format check."""
    assert normalize_employee_id("  E999  ") == "E999"


def test_normalize_rejects_wrong_length() -> None:
    """Not exactly three digits is not an id."""
    assert normalize_employee_id("E20") is None
    assert normalize_employee_id("E2011") is None
    assert normalize_employee_id("201") is None
    assert normalize_employee_id("e202x") is None


def test_normalize_rejects_empty() -> None:
    """Empty and whitespace-only are not ids."""
    assert normalize_employee_id("") is None
    assert normalize_employee_id("   ") is None


def test_prompt_employee_id_retries_empty_and_malformed() -> None:
    """Empty and bad shapes re-prompt. A valid id is normalized."""
    answers = iter(["", "  ", "e20", "e201"])
    printed: list[str] = []

    result = prompt_employee_id(
        input_fn=lambda _: next(answers),
        print_fn=lambda text: printed.append(text),
    )

    assert result == "E201"
    assert printed


def test_prompt_query_retries_empty() -> None:
    """Query is prompted until the line is not empty after strip."""
    answers = iter(["", "  ", "I need a monitor."])

    result = prompt_query(input_fn=lambda _: next(answers))

    assert result == "I need a monitor."


def _run_main(monkeypatch, argv: list[str], *, inputs: list[str] | None = None) -> list[tuple[str, str]]:
    """Run main with a fake adapter and capture run_request arguments."""
    calls: list[tuple[str, str]] = []

    async def fake_run(employee_id: str, query: str, adapter: object, **kwargs: object) -> dict:
        calls.append((employee_id, query))
        return {}

    monkeypatch.setattr("mcp_vedanti.host.__main__.run_request", fake_run)
    monkeypatch.setattr("mcp_vedanti.host.__main__.load_adapter", lambda: object())
    monkeypatch.setattr(sys, "argv", argv)
    if inputs is not None:
        queued = iter(inputs)
        monkeypatch.setattr("builtins.input", lambda _: next(queued))
    main()
    return calls


def test_flags_normalize_employee_id(monkeypatch) -> None:
    """A well-formed flag id is capitalized before the request runs."""
    calls = _run_main(
        monkeypatch,
        ["prog", "--employee-id", "e201", "--query", "I need a second monitor."],
    )

    assert calls == [("E201", "I need a second monitor.")]


def test_malformed_flag_id_exits(monkeypatch) -> None:
    """A flag id that is not E plus three digits is an error."""
    monkeypatch.setattr("mcp_vedanti.host.__main__.load_adapter", lambda: object())
    monkeypatch.setattr(sys, "argv", ["prog", "--employee-id", "e20", "--query", "I need a monitor."])

    with pytest.raises(SystemExit):
        main()


def test_interactive_prompts_when_flags_are_omitted(monkeypatch) -> None:
    """No flags means prompt for both fields."""
    calls = _run_main(
        monkeypatch,
        ["prog"],
        inputs=["e205", "I need a laptop."],
    )

    assert calls == [("E205", "I need a laptop.")]


def test_missing_query_flag_is_prompted(monkeypatch) -> None:
    """A valid id flag still prompts for a missing query."""
    calls = _run_main(
        monkeypatch,
        ["prog", "--employee-id", "E204"],
        inputs=["I need a dock."],
    )

    assert calls == [("E204", "I need a dock.")]


def test_queries_flag_still_runs_saved_rows(monkeypatch) -> None:
    """--queries does not prompt and still walks the saved file."""
    seen: list[str] = []

    async def fake_run(employee_id: str, query: str, adapter: object, **kwargs: object) -> dict:
        seen.append(employee_id)
        return {}

    async def fake_saved(**kwargs: object) -> None:
        await fake_run("E201", "I need a second monitor.", object())

    monkeypatch.setattr("mcp_vedanti.host.__main__._saved", fake_saved)
    monkeypatch.setattr("mcp_vedanti.host.__main__.load_adapter", lambda: object())
    monkeypatch.setattr(sys, "argv", ["prog", "--queries"])
    main()

    assert seen == ["E201"]


def test_saved_rows_normalize_employee_id(monkeypatch) -> None:
    """Each saved row id is normalized the same way as a flag."""
    calls: list[tuple[str, str]] = []

    async def fake_run(employee_id: str, query: str, adapter: object, **kwargs: object) -> dict:
        calls.append((employee_id, query))
        return {}

    monkeypatch.setattr("mcp_vedanti.host.__main__.run_request", fake_run)
    monkeypatch.setattr("mcp_vedanti.host.__main__.load_adapter", lambda: object())
    monkeypatch.setattr(
        "mcp_vedanti.host.__main__.json.loads",
        lambda _: [{"employee_id": "e202", "query": "I need a new monitor."}],
    )

    from mcp_vedanti.host.__main__ import _saved

    asyncio.run(_saved(run_dir=None))

    assert calls == [("E202", "I need a new monitor.")]


def test_check_without_queries_exits(monkeypatch) -> None:
    """--check is only valid with --queries."""
    monkeypatch.setattr(sys, "argv", ["prog", "--check"])

    with pytest.raises(SystemExit):
        main()


def test_golden_mismatch_is_none_when_class_matches() -> None:
    """Null status and escalate match a no-item golden row."""
    row = {
        "employee_id": "E203",
        "query": "I know it's early, please approve it anyway.",
        "status": None,
        "decision": "escalate",
    }
    result = {"status": None, "decision": "escalate", "stop": "draft"}

    assert _golden_mismatch(row, result) is None


def test_golden_mismatch_names_a_step_limit() -> None:
    """A timed-out run fails the check even if a status leaked in."""
    row = {"status": "in_policy", "decision": "approve"}
    result = {"status": "in_policy", "decision": None, "stop": "step_limit"}

    assert _golden_mismatch(row, result) == "stop=step_limit"


def test_saved_check_exits_when_a_row_misses(monkeypatch) -> None:
    """--queries --check fails after a wrong class."""

    async def fake_run(employee_id: str, query: str, adapter: object, **kwargs: object) -> dict:
        return {"status": "out_of_policy", "decision": "deny", "stop": "draft"}

    monkeypatch.setattr("mcp_vedanti.host.__main__.run_request", fake_run)
    monkeypatch.setattr("mcp_vedanti.host.__main__.load_adapter", lambda: object())
    monkeypatch.setattr(
        "mcp_vedanti.host.__main__.json.loads",
        lambda _: [
            {
                "employee_id": "E201",
                "query": "I need a second monitor.",
                "status": "in_policy",
                "decision": "approve",
            }
        ],
    )

    from mcp_vedanti.host.__main__ import _saved

    with pytest.raises(SystemExit) as exited:
        asyncio.run(_saved(run_dir=None, check=True))

    assert exited.value.code == 1


def test_saved_check_passes_when_every_row_matches(monkeypatch) -> None:
    """--queries --check stays silent when status and decision match."""

    async def fake_run(employee_id: str, query: str, adapter: object, **kwargs: object) -> dict:
        return {"status": "in_policy", "decision": "approve", "stop": "draft"}

    monkeypatch.setattr("mcp_vedanti.host.__main__.run_request", fake_run)
    monkeypatch.setattr("mcp_vedanti.host.__main__.load_adapter", lambda: object())
    monkeypatch.setattr(
        "mcp_vedanti.host.__main__.json.loads",
        lambda _: [
            {
                "employee_id": "E201",
                "query": "I need a second monitor.",
                "status": "in_policy",
                "decision": "approve",
            }
        ],
    )

    from mcp_vedanti.host.__main__ import _saved

    asyncio.run(_saved(run_dir=None, check=True))

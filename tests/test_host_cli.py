"""Confirm host CLI prompts, id format, and normalization. No Ollama or server."""

import asyncio
import sys

import pytest

from mcp_vedanti.host.__main__ import (
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

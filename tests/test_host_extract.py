"""Confirm the pre-ReAct extract parser. No Ollama or server."""

from mcp_vedanti.host.extract import extract_prompt, parse_extract


def test_parse_one_item() -> None:
    """A single item is stored as item."""
    assert parse_extract(
        '{"thought": "They asked for a headset.", "item": "headset"}'
    ) == {"thought": "They asked for a headset.", "item": "headset"}


def test_parse_normalizes_item_case_and_space() -> None:
    """The bound item is stripped and lowercased. Synonyms are not rewritten here."""
    assert parse_extract(
        '{"thought": "Keep their word.", "item": " Headphones "}'
    ) == {"thought": "Keep their word.", "item": "headphones"}


def test_parse_null_item() -> None:
    """No equipment word is item null."""
    assert parse_extract(
        '{"thought": "No item is named.", "item": null}'
    ) == {"thought": "No item is named.", "item": None}


def test_parse_two_items() -> None:
    """Two named items are stored as items, each normalized."""
    assert parse_extract(
        '{"thought": "They named two.", "items": [" Monitor ", "LAPTOP"]}'
    ) == {"thought": "They named two.", "items": ["monitor", "laptop"]}


def test_parse_strips_fenced_json() -> None:
    """A fenced block is still one extract object."""
    text = """```json
{"thought": "One item.", "item": "keyboard"}
```"""
    assert parse_extract(text) == {"thought": "One item.", "item": "keyboard"}


def test_parse_rejects_empty_item_string() -> None:
    """An empty item string is not a bound item."""
    assert parse_extract('{"thought": "Empty.", "item": "  "}') is None


def test_parse_rejects_one_entry_items_list() -> None:
    """A single name must use item, not items."""
    assert parse_extract('{"thought": "One.", "items": ["monitor"]}') is None


def test_parse_rejects_item_and_items_together() -> None:
    """item and items cannot both be present."""
    assert (
        parse_extract(
            '{"thought": "Both.", "item": "monitor", "items": ["laptop"]}'
        )
        is None
    )


def test_parse_rejects_missing_thought() -> None:
    """Thought is required, same as a ReAct step."""
    assert parse_extract('{"item": "monitor"}') is None


def test_parse_rejects_tool_shape() -> None:
    """A ReAct tool call is not an extract result."""
    assert (
        parse_extract(
            '{"thought": "Lookup.", "tool": "get_employee_info", "arguments": {}}'
        )
        is None
    )


def test_parse_rejects_draft_shape() -> None:
    """A ReAct draft is not an extract result."""
    assert parse_extract('{"thought": "Done.", "draft": "Approved."}') is None


def test_parse_rejects_garbage() -> None:
    """Text that is not one JSON object is unusable."""
    assert parse_extract("headset") is None


def test_extract_prompt_states_synonym_and_non_rename_rules() -> None:
    """The extract prompt allows same-device synonyms and forbids a computer-to-laptop rewrite."""
    text = extract_prompt()
    assert "headphones" in text.lower()
    assert "headset" in text.lower()
    assert "computer" in text.lower()
    assert "laptop" in text.lower()

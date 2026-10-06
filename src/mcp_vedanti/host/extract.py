"""Name the item in the query before the ReAct loop starts."""

import json


def extract_prompt() -> str:
    """Instructions for the one extract call. Not a tool catalog."""
    return _INSTRUCTIONS


def parse_extract(text: str) -> dict | None:
    """Return a thought plus one item, no item, or two or more items."""
    raw = _unwrap_fence(text)
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict) or not isinstance(body.get("thought"), str):
        return None
    if "tool" in body or "draft" in body:
        return None
    has_item = "item" in body
    has_items = "items" in body
    if has_item == has_items:
        return None
    thought = body["thought"]
    if has_item:
        item = _one_item(body["item"])
        if item is False:
            return None
        return {"thought": thought, "item": item}
    names = _item_list(body["items"])
    if names is None:
        return None
    return {"thought": thought, "items": names}


def _unwrap_fence(text: str) -> str:
    """Drop a surrounding markdown fence if the model wrapped the JSON."""
    raw = text.strip()
    if not raw.startswith("```"):
        return raw
    lines = raw.splitlines()[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _one_item(value: object) -> str | None | bool:
    """Return a normalized item, None for JSON null, or False when unusable."""
    if value is None:
        return None
    if not isinstance(value, str):
        return False
    item = value.strip().lower()
    if not item:
        return False
    return item


def _item_list(value: object) -> list[str] | None:
    """Return two or more normalized names, or None when the list is unusable."""
    if not isinstance(value, list) or len(value) < 2:
        return None
    names = []
    for entry in value:
        item = _one_item(entry)
        if not isinstance(item, str):
            return None
        names.append(item)
    return names


_INSTRUCTIONS = """\
Read the employee's query. Name the equipment they are asking for.

Reply with one JSON object and nothing else.

One item:
{"thought": "why this is one device", "item": "<equipment word>"}

No item:
{"thought": "why nothing is named", "item": null}

Two or more different items:
{"thought": "why there is more than one", "items": ["<first>", "<second>"]}

Use items only when they asked for two or more devices. One name uses item.

Same-device everyday words become the usual equipment word. Headphones and headphone become headset.

Do not rename a different device. Computer is not a laptop. Do not invent a catalog item from a plea with no equipment word.

Do not call a tool. Do not write a draft.
"""

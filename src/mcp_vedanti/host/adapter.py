"""Model calls for the host. Ollama details stay in this module."""

import json
import urllib.request
from pathlib import Path
from typing import Protocol


class ModelAdapter(Protocol):
    """One completion over a transcript. Callers do not see the provider."""

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Return the assistant reply text for this transcript."""


class OllamaAdapter:
    """Call a local Ollama chat model and return the reply text."""

    def __init__(self, model: str, base_url: str, *, think: bool) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.think = think

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Post one chat request and return message content."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": self.think,
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.load(response)
        return body["message"]["content"]


def load_config(path: Path | None = None) -> dict:
    """Read the host config next to this module, unless path is set."""
    config_path = path or Path(__file__).with_name("config.json")
    return json.loads(config_path.read_text())


def load_adapter(path: Path | None = None) -> OllamaAdapter:
    """Build the Ollama adapter from the host config."""
    config = load_config(path)
    return OllamaAdapter(
        model=config["model"],
        base_url=config["base_url"],
        think=config["think"],
    )

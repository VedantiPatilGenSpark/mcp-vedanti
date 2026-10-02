"""MCP client for the equipment server.

The rest of the host calls this module. SDK types stay here.
"""

from mcp import Client

SERVER_URL = "http://127.0.0.1:8000/mcp"


class EquipmentClient:
    """Connection to the equipment server."""

    def __init__(self, url: str = SERVER_URL) -> None:
        self.url = url
        self._client: Client | None = None

    async def __aenter__(self) -> "EquipmentClient":
        self._client = Client(self.url)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    async def list_tools(self) -> list[dict]:
        """Return each tool's name, description, and argument schema."""
        listed = await self._connection().list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": dict(tool.input_schema),
            }
            for tool in listed.tools
        ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Call one tool. text is the observation. is_error means the server rejected it."""
        result = await self._connection().call_tool(name, arguments)
        parts = [block.text for block in result.content if getattr(block, "text", None)]
        return {"text": "\n".join(parts), "is_error": bool(result.is_error)}

    def _connection(self) -> Client:
        if self._client is None:
            raise RuntimeError("EquipmentClient is not connected.")
        return self._client

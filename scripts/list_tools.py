import anyio
from mcp import Client

async def main() -> None:
    async with Client("http://127.0.0.1:8000/mcp") as client:
        listed = await client.list_tools()
        for tool in listed.tools:
            print(tool.name)
            print(tool.description)
            print(tool.input_schema)

anyio.run(main)
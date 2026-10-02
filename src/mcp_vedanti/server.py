from mcp.server import MCPServer

mcp = MCPServer("mcp-vedanti")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def main() -> None:
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()
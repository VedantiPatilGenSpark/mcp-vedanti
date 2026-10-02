from mcp.server import MCPServer

from mcp_vedanti.equipment import (
    check_request_eligibility,
    flag_for_human_review,
    get_employee_info,
    get_policy_limits,
)

mcp = MCPServer("mcp-vedanti")

mcp.tool()(get_employee_info)
mcp.tool()(get_policy_limits)
mcp.tool()(check_request_eligibility)
mcp.tool()(flag_for_human_review)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()

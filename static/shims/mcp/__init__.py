"""Browser-side stand-in for the `mcp` package.

`milp_mcp_server.py` builds a FastMCP server at import time and `mcp_clients.py`
imports `StdioServerParameters`. The static build never speaks MCP — it calls
`solve_daily_milp` directly — so only the import-time surface is provided.
"""


class StdioServerParameters:
    def __init__(self, command=None, args=None, env=None, **kwargs):
        self.command = command
        self.args = list(args or [])
        self.env = env or {}


__all__ = ["StdioServerParameters"]

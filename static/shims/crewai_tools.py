"""Browser-side stand-in for `crewai_tools`.

`mcp_clients.py` imports `MCPServerAdapter` at module import time. The Dash app
never reaches the MCP client code paths, so a stub is enough to let the module
load.
"""


class MCPServerAdapter:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("MCP transport is not available in the static build")

    def __enter__(self):
        raise RuntimeError("MCP transport is not available in the static build")

    def __exit__(self, *args):
        return False

"""Browser-side stand-in for `mcp.server.fastmcp.FastMCP`.

`milp_mcp_server.py` decorates its two functions with `@mcp.tool()` and only
calls `mcp.run()` under `if __name__ == "__main__"`, which never happens here.
The decorator therefore just needs to return the function unchanged.
"""


class FastMCP:
    def __init__(self, name=None, **kwargs):
        self.name = name
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn

        if args and callable(args[0]):
            return register(args[0])
        return register

    def run(self, *args, **kwargs):
        raise RuntimeError("MCP transport is not available in the static build")

    def run_async(self, *args, **kwargs):
        raise RuntimeError("MCP transport is not available in the static build")

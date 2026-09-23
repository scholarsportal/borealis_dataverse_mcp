import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import mcp
except ModuleNotFoundError:
    mcp = types.ModuleType("mcp")
    server_mod = types.ModuleType("mcp.server")
    stdio_mod = types.ModuleType("mcp.server.stdio")
    types_mod = types.ModuleType("mcp.types")

    class Server:
        def __init__(self, *args, **kwargs): pass
        def list_tools(self): return lambda fn: fn
        def call_tool(self): return lambda fn: fn

    class Tool:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)

    class TextContent:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)

    async def stdio_server():
        raise RuntimeError("stub")

    server_mod.Server = Server
    stdio_mod.stdio_server = stdio_server
    types_mod.Tool = Tool
    types_mod.TextContent = TextContent
    sys.modules.update({
        "mcp": mcp,
        "mcp.server": server_mod,
        "mcp.server.stdio": stdio_mod,
        "mcp.types": types_mod,
    })

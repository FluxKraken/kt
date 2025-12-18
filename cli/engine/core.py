import lupa
from lupa import LuaRuntime
from cli.engine.actions import Actions
from typing import Dict, Any, Optional

class RecipeEngine:
    def __init__(self, context: Dict[str, Any] = None, mode: str = "EXECUTE"):
        """
        mode: "EXECUTE" or "GENERATE_CONFIG"
        """
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.context = context or {}
        self.mode = mode
        self.actions = Actions(self)
        self.script_content = ""
        
    def execute(self, script_content: str):
        self.script_content = script_content
        # Setup 'r' table
        r = self.lua.table()
        
        # Bind actions
        r.declare = self.actions.declare
        r.prompt = self.actions.prompt
        r.template = self.actions.template
        r.assets = self.actions.assets
        r.command = self.actions.command
        r.run = self.actions.run
        r.gate = self.actions.gate
        r.touch = self.actions.touch
        r.mkdir = self.actions.mkdir
        r.f = self.actions.f
        r.ref = self.actions.ref
        r.splice = self.actions.splice
        
        self.lua.globals().r = r
        
        # Execute script
        try:
            self.lua.execute(script_content)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Lua execution error: {e}")

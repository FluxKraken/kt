import lupa
from lupa import LuaRuntime
from cli.engine.actions import Actions
from typing import Dict, Any, Optional
import os
import toml
from collections import OrderedDict

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
        r.recipe = self.actions.recipe
        
        self.lua.globals().r = r
        
        # Execute script
        try:
            self.lua.execute(script_content)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Lua execution error: {e}")

    def render(self, output_path: Optional[str] = None):
        """
        Finalize the recipe rendering process. 
        If mode is GENERATE_CONFIG, write the collected prompts to output_path.
        """
        if self.mode == "GENERATE_CONFIG":
            if not output_path:
                raise ValueError("output_path is required for GENERATE_CONFIG mode")

            def deep_filter(mask, source):
                result = OrderedDict()
                for k, v in mask.items():
                    if isinstance(v, dict):
                        if k in source and isinstance(source[k], dict):
                            nested = deep_filter(v, source[k])
                            if nested:
                                result[k] = nested
                    else:
                        # Leaf
                        if k in source:
                            result[k] = source[k]
                        else:
                            result[k] = v
                return result

            final_output = deep_filter(self.actions.collected_prompts, self.context)
            
            # Use toml.dump with OrderedDict support if possible
            # Standard toml library supports OrderedDict if passed directly
            with open(output_path, 'w') as f:
                toml.dump(final_output, f)
            return True
        return False

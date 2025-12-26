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
        self.config_template = None
        
    def execute(self, script_content: str):
        self.script_content = script_content
        # Setup 'r' table
        r = self.lua.table()
        
        # Bind actions
        # Bind actions
        r.declare = self.actions.declare
        r.config = self.actions.config
        r.question = self.actions.question
        r.confirm = self.actions.confirm
        r.template = self.actions.template
        r.asset = self.actions.asset
        r.run = self.actions.run
        r.touch = self.actions.touch
        r.eval = self.actions.eval

        r.mkdir = self.actions.mkdir
        r.delete = self.actions.delete
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

    def render(self, output_path: Optional[str] = None, output_format: str = "toml"):
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

            if self.config_template:
                # Render using the stored template logic
                # We need to render the template with the collected context
                from cli.engine.jinja_utils import render_template_with_shell
                
                # Combine collected prompts and context
                render_context = self.context.copy()
                render_context.update(self.actions.collected_prompts)
                
                # Convert to python objects for Jinja
                render_context = self.actions._lua_to_python(render_context)
                
                rendered = render_template_with_shell(self.config_template, render_context)
                
                with open(output_path, 'w') as f:
                    f.write(rendered)
            else:
                final_output = deep_filter(self.actions.collected_prompts, self.context)
                normalized_format = (output_format or "toml").lower()

                if normalized_format == "toml":
                    # Use toml.dump with OrderedDict support if possible
                    # Standard toml library supports OrderedDict if passed directly
                    with open(output_path, 'w') as f:
                        toml.dump(final_output, f)
                elif normalized_format in ("yaml", "yml"):
                    import yaml
                    with open(output_path, 'w') as f:
                        yaml.safe_dump(final_output, f, sort_keys=False)
                else:
                    raise ValueError(f"Unsupported config format: {output_format}")

            return True
        return False

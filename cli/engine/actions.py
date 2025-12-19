import click
import subprocess
import os
import toml
import re
from typing import Dict, Any, List
from jinja2 import Template as JinjaTemplate
from rich.console import Console
from collections import OrderedDict

console = Console()

class Actions:
    def __init__(self, engine):
        self.engine = engine
        self.collected_prompts = OrderedDict()
        self.prompt_call_count = 0
        
    def _resolve_var(self, path: str):
        """Resolve a dot-notation path in self.engine.context"""
        parts = path.split('.')
        curr = self.engine.context
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return None
        return curr

    def f(self, format_str):
        """Format string with $(variable) substitution"""
        # Simple implementation, can be improved to support full python format or complex logic
        # For now, simplistic manual parsing or string.format?
        # User example: r.f("$(project.location)/README.md")
        # Let's use a custom replacer
        def replace(match):
            key = match.group(1)
            val = self._resolve_var(key)
            return str(val) if val is not None else ""
            
        import re
        return re.sub(r'\$\(([\w.]+)\)', replace, format_str)

    def ref(self, path):
         """Return value of variable at path"""
         val = self._resolve_var(path)
         return val if val is not None else ""

    def splice(self, path):
        """Return list at path"""
        val = self._resolve_var(path)
        # Ensure it's a python list/tuple before returning
        python_val = self._lua_to_python(val)
        if isinstance(python_val, list):
            return tuple(python_val)
        return (python_val,) if python_val is not None and python_val != "" else ()

    def _lua_to_python(self, obj):
        """Recursively convert Lua tables to Python dicts/lists"""
        if hasattr(obj, 'items'): # Lua table / Dict
            # Check if it's a list-like table (integer keys starting 1)
            # This is heuristic. Lupa tables support iteration.
            # Simpler: convert to dict. If user intended list, it's tricky in Lua vs Python.
            # Lupa unpack_returned_tuples=True helps somewhat.
            # Let's assume dict for declare/prompt structure.
            # But dependencies.prod is a list.
            # If we do dict(obj), list-like table becomes {1: v1, 2: v2}
            try:
                # Try to convert to list if keys are sequential integers
                d = dict(obj)
                if not d: return d
                if all(isinstance(k, int) for k in d.keys()):
                     # Sort by key
                     return [self._lua_to_python(d[k]) for k in sorted(d.keys())]
                return {k: self._lua_to_python(v) for k, v in d.items()}
            except:
                return obj
        elif isinstance(obj, (list, tuple)):
            return [self._lua_to_python(x) for x in obj]
        return obj

    def declare(self, args):
        """Declare variables"""
        # args is a lua table/dict
        # We merge into context
        def merge(target, source):
            for k, v in source.items():
                if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                    merge(target[k], v)
                else:
                    target[k] = v
        
        data = self._lua_to_python(args)
        
        merge(self.engine.context, data)

    def prompt(self, args):
        """Handle prompting"""
        # args: dict of variable definitions
        schema = dict(args)
        self.prompt_call_count += 1

        # Heuristic to find the correct r.prompt block in the script
        prompts_found = list(re.finditer(r'r\.prompt\s*\(\{', self.engine.script_content))
        if len(prompts_found) >= self.prompt_call_count:
            start_index = prompts_found[self.prompt_call_count - 1].start()
            depth = 0
            started = False
            end_index = -1
            for i in range(start_index, len(self.engine.script_content)):
                char = self.engine.script_content[i]
                if char == '(':
                    depth += 1
                    started = True
                elif char == ')':
                    depth -= 1
                
                if started and depth == 0:
                    end_index = i + 1
                    break
            
            prompt_block = self.engine.script_content[start_index:end_index] if end_index != -1 else ""
        else:
            prompt_block = ""

        def get_key_order(text, keys):
            # Find the position of each key in the text
            key_positions = []
            for k in keys:
                # regex to find key = or key= or "key" = or ['key'] =
                # We also look for start of line or space before key
                pattern = rf'(?:^|\s|[,{{])(?:\[\s*["\']{re.escape(k)}["\']\s*\]|["\']?{re.escape(k)}["\']?)\s*='
                match = re.search(pattern, text)
                if match:
                    key_positions.append((k, match.start()))
                else:
                    key_positions.append((k, float('inf')))
            
            return [k for k, pos in sorted(key_positions, key=lambda x: x[1])]

        # Recursive helper to process schema
        def process_node(node_schema, current_path=None, block_text=""):
            result = OrderedDict()
            has_prompt = False
            
            node_dict = dict(node_schema)
            keys_to_process = [k for k in node_dict.keys() if k != "_comment"]
            
            if block_text:
                ordered_keys = get_key_order(block_text, keys_to_process)
            else:
                ordered_keys = keys_to_process

            for key in ordered_keys:
                val = node_dict[key]
                val_dict = dict(val) if hasattr(val, 'items') or hasattr(val, 'keys') else None
                
                if val_dict is not None and 'default' in val_dict:
                    # Leaf node
                    full_path = f"{current_path}.{key}" if current_path else key
                    curr_val = self._resolve_var(full_path)
                    
                    if curr_val is None:
                        has_prompt = True
                        result[key] = self._lua_to_python(val_dict.get('default'))
                    else:
                        result[key] = self._lua_to_python(curr_val)
                        
                elif val_dict is not None:
                    # Nested section
                    new_path = f"{current_path}.{key}" if current_path else key
                    
                    nested_block = ""
                    if block_text:
                        pattern = rf'(?:\[\s*["\']?{re.escape(key)}["\']?\s*\]|["\']?{re.escape(key)}["\']?)\s*='
                        match = re.search(pattern, block_text)
                        if match:
                            s_idx = block_text.find('{', match.end())
                            if s_idx != -1:
                                d = 0
                                e_idx = -1
                                for i in range(s_idx, len(block_text)):
                                    c = block_text[i]
                                    if c == '{': d += 1
                                    elif c == '}': d -= 1
                                    if d == 0:
                                        e_idx = i + 1
                                        break
                                if e_idx != -1:
                                    nested_block = block_text[s_idx:e_idx]

                    child_result, child_has_prompt = process_node(val_dict, new_path, nested_block)
                    if child_has_prompt:
                        has_prompt = True
                    result[key] = child_result
            
            return result, has_prompt

        if self.engine.mode == "GENERATE_CONFIG":
            # Just accumulate defaults into context
             defaults, _ = process_node(schema, block_text=prompt_block)
             
             # We need to merge defaults deep into context AND collected_prompts
             def deep_merge(target, source):
                 for k, v in source.items():
                     if isinstance(v, dict):
                         if k not in target: target[k] = OrderedDict()
                         if isinstance(target[k], dict):
                             deep_merge(target[k], v)
                         else:
                             target[k] = v
                     else:
                         target[k] = v
                          
             deep_merge(self.engine.context, defaults)
             deep_merge(self.collected_prompts, defaults)
             return

        # EXECUTE MODE
        defaults_data, needs_prompt = process_node(schema, block_text=prompt_block)

        if needs_prompt:
             # Create temp toml
             header = "# Please fill in the values.\n\n"
             toml_str = toml.dumps(defaults_data)
             
             new_toml = click.edit(header + toml_str, extension=".toml")
             if new_toml:
                 new_data = toml.loads(new_toml)
                 # Merge back into context
                 def deep_merge(target, source):
                     for k, v in source.items():
                         if isinstance(v, dict):
                             if k not in target: target[k] = OrderedDict()
                             if isinstance(target[k], dict):
                                 deep_merge(target[k], v)
                             else:
                                 target[k] = v
                         else:
                             target[k] = v
                 deep_merge(self.engine.context, new_data)
             else:
                 console.print("[yellow]No input provided, using defaults.[/yellow]")
                 # Merge defaults
                 def deep_merge(target, source):
                     for k, v in source.items():
                         if isinstance(v, dict):
                             if k not in target: target[k] = OrderedDict()
                             if isinstance(target[k], dict):
                                 deep_merge(target[k], v)
                             else:
                                 target[k] = v
                         else:
                             target[k] = v
                 deep_merge(self.engine.context, defaults_data)
        else:
            pass

    def template(self, name, args):
        """Render template"""
        if self.engine.mode == "GENERATE_CONFIG": return

        args = dict(args)
        output = args.get("output")
        overwrite = args.get("overwrite", False)
        context = args.get("context", {})
        
        if not output:
             console.print(f"[red]Template action missing output path.[/red]")
             return
             
        # Resolve 'name'. Name might be "project::template_name" or just "template_name"
        # If "::", first part is project name.
        proj_name = None
        tmpl_name = name
        if "::" in name:
            proj_name, tmpl_name = name.split("::")
            
        # Fetch template
        from cli.db.session import get_session
        from cli.db.models import Template, Project
        from sqlmodel import select
        
        with get_session() as session:
            query = select(Template).where(Template.name == tmpl_name)
            if proj_name:
                proj = session.exec(select(Project).where(Project.name == proj_name)).first()
                if proj:
                     query = query.where(Template.project_id == proj.id)
            
            tmpl_obj = session.exec(query).first()
            if not tmpl_obj:
                console.print(f"[red]Template '{name}' not found.[/red]")
                return
                
            template_content = tmpl_obj.content
            
        # Render
        try:
             from cli.engine.jinja_utils import render_template_with_shell
             rendered = render_template_with_shell(template_content, context)
             
             # Ensure directory exists
             out_dir = os.path.dirname(output)
             if out_dir and not os.path.exists(out_dir):
                 os.makedirs(out_dir)
                 
             if os.path.exists(output) and not overwrite:
                 console.print(f"[yellow]Skipping template '{output}', exists.[/yellow]")
                 return
                 
             with open(output, 'w') as f:
                 f.write(rendered)
             console.print(f"[green]Rendered {output}[/green]")
        except Exception as e:
            console.print(f"[red]Error rendering template {name}: {e}[/red]")

    def assets(self, name, args):
        """Copy asset"""
        if self.engine.mode == "GENERATE_CONFIG": return
        
        args = dict(args)
        destination = args.get("destination")
        overwrite = args.get("overwrite", False)
        
        if not destination:
             console.print(f"[red]Asset action missing destination.[/red]")
             return

        proj_name = None
        asset_name = name
        if "::" in name:
            proj_name, asset_name = name.split("::")

        from cli.db.session import get_session
        from cli.db.models import Asset, Project
        from sqlmodel import select
        
        with get_session() as session:
            query = select(Asset).where(Asset.name == asset_name)
            if proj_name:
                proj = session.exec(select(Project).where(Project.name == proj_name)).first()
                if proj:
                     query = query.where(Asset.project_id == proj.id)
            
            asset_obj = session.exec(query).first()
            if not asset_obj:
                console.print(f"[red]Asset '{name}' not found.[/red]")
                return
                
            content = asset_obj.content

        # Ensure directory
        out_dir = os.path.dirname(destination)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
        if os.path.exists(destination) and not overwrite:
             console.print(f"[yellow]Skipping asset '{destination}', exists.[/yellow]")
             return
             
        with open(destination, 'wb') as f:
            f.write(content)
        console.print(f"[green]Copied asset {destination}[/green]")

    def command(self, args, func):
        """Command block"""
        args = dict(args)
        check_var = args.get("check")
        
        if check_var:
            val = self._resolve_var(check_var)
            if not val:
                return # Skip
        
        # Execute the Lua function block
        # In Lupa, 'func' is a Lua function. We call it.
        if self.engine.mode == "GENERATE_CONFIG": 
            # Do we execute command blocks in config gen mode?
            # Probably not, as they contain r.run() side effects.
            return
            
        func()

    def run(self, cmd_args, options=None):
        """Run subprocess"""
        if self.engine.mode == "GENERATE_CONFIG": return

        # cmd_args is list of strings
        # options might have cwd
        
        # Use _lua_to_python to handle command arguments reliably
        cmd_list = self._lua_to_python(cmd_args)
        if not isinstance(cmd_list, list):
            cmd_list = [cmd_list]
        
        opts = dict(options) if options else {}
        cwd = opts.get("cwd")
        
        console.print(f"[dim]Running: {' '.join(str(x) for x in cmd_list)}[/dim]")
        
        try:
            subprocess.run(cmd_list, cwd=cwd, check=True)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Command failed: {e}[/red]")
            # Should we raise? use 'gate'?

    def gate(self, args):
        """Gate execution via user prompt"""
        args = dict(args)
        prompt_text = args.get("prompt", "Continue?")
        default = args.get("default", True)
        store = args.get("store")
        
        if self.engine.mode == "GENERATE_CONFIG":
             # Use default
             if store:
                 self.engine.context[store] = default
             return default

        # In Execute mode
        # If variable already exists (e.g. from config), use it?
        # Gate usually implies "ask now", but if we want reproducibility...
        # Let's check context first?
        if store and store in self.engine.context:
             return self.engine.context[store]
             
        response = click.confirm(prompt_text, default=default)
        
        if store:
            self.engine.context[store] = response
            
        return response

    def touch(self, raw_path, options=None):
        """Create a file with optional content"""
        if self.engine.mode == "GENERATE_CONFIG": return

        path = self.f(raw_path)
        opts = dict(options) if options else {}
        content = opts.get("content", "")
        if content:
            content = self.f(content)
        overwrite = opts.get("overwrite", False)

        # Ensure directory exists
        out_dir = os.path.dirname(path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if os.path.exists(path) and not overwrite:
            console.print(f"[yellow]Skipping touch '{path}', exists.[/yellow]")
            return

        with open(path, 'w') as f:
            f.write(content)
        console.print(f"[green]Touched {path}[/green]")

    def mkdir(self, raw_path, options=None):
        """Create a directory"""
        if self.engine.mode == "GENERATE_CONFIG": return

        path = self.f(raw_path)
        opts = dict(options) if options else {}
        parents = opts.get("parents", False)

        if os.path.exists(path):
            if os.path.isdir(path):
                # Already exists, nothing to do
                return
            else:
                console.print(f"[red]Cannot create directory '{path}', a file exists at this path.[/red]")
                return

        try:
            if parents:
                os.makedirs(path, exist_ok=True)
            else:
                os.mkdir(path)
            console.print(f"[green]Created directory {path}[/green]")
        except Exception as e:
            console.print(f"[red]Error creating directory {path}: {e}[/red]")

import click
import subprocess
import os
import toml
from typing import Dict, Any, List
from jinja2 import Template as JinjaTemplate
from rich.console import Console

console = Console()

class Actions:
    def __init__(self, engine):
        self.engine = engine
        self.collected_prompts = {}
        
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
        if hasattr(val, 'values'): # It's a lua table/dict
             return tuple(val.values())
        return tuple(val) if isinstance(val, list) else ()

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
        
        # If we are in GENERATE_CONFIG mode, we just collect the schema and defaults
        if self.engine.mode == "GENERATE_CONFIG":
            # Just accumulate defaults into context so script can continue conceptually
            # And store schema for export
            for section, fields in schema.items():
                if section not in self.engine.context:
                    self.engine.context[section] = {}
                self.collected_prompts[section] = fields
                
                fields_dict = dict(fields)
                for field_name, field_def in fields_dict.items():
                    if field_name == "_comment": continue
                    field_def_dict = dict(field_def)
                    default = field_def_dict.get('default')
                    self.engine.context[section][field_name] = default
            return

        # If EXECUTE mode
        # Check if we already have values in context (e.g. loaded from config)
        # We assume context is already populated with config if provided.
        # But we might need to prompt for missing values.
        
        # Simplified: If any key in this prompt block is MISSING from context, trigger prompt.
        # BUT user requirement says: "generate a temporary toml document and use click to open an editor"
        
        # First, generate defaults dict
        defaults_data = {}
        needs_prompt = False
        
        for section, fields in schema.items():
            defaults_data[section] = {}
            fields_dict = dict(fields)
            for field_name, field_def in fields_dict.items():
                if field_name == "_comment": continue
                field_def_dict = dict(field_def)
                
                # Check if exists in context
                curr_val = self._resolve_var(f"{section}.{field_name}")
                if curr_val is None:
                    needs_prompt = True
                    defaults_data[section][field_name] = field_def_dict.get('default')
                else:
                    defaults_data[section][field_name] = curr_val

        if needs_prompt:
             # Create temp toml
             header = "# Please fill in the values.\n\n"
             toml_str = toml.dumps(defaults_data)
             
             new_toml = click.edit(header + toml_str, extension=".toml")
             if new_toml:
                 new_data = toml.loads(new_toml)
                 # Merge back into context
                 for k, v in new_data.items():
                     if k not in self.engine.context:
                         self.engine.context[k] = {}
                     self.engine.context[k].update(v)
             else:
                 console.print("[yellow]No input provided, using defaults.[/yellow]")
                 # Merge defaults
                 for k, v in defaults_data.items():
                     if k not in self.engine.context:
                         self.engine.context[k] = {}
                     self.engine.context[k].update(v)
        else:
            # Maybe update context with found values to ensure consistency?
            # It's already in context.
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
        
         # Lupa converts Lua tables to python objects that support iteration/indexing
         # But we should be safe converting to list/dict
        cmd_list = list(cmd_args.values()) if hasattr(cmd_args, 'values') else list(cmd_args)
        
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

import click
import os
from rich.console import Console
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Project

console = Console()

@click.command("r")
@click.argument("name", required=False)
@click.option("--config", help="TOML config file")
@click.option("--create-config", help="Path to create a new config file")
@click.option("--output", help="Output path for generated config (deprecated, use --create-config)")
def r_cmd(name, config, create_config, output):
    """Executes the default recipe for the specified project."""
    import toml
    import json
    from cli.engine.core import RecipeEngine

    # Handle deprecated output arg gracefully by mapping to create_config if not handled
    if output and not create_config:
        create_config = output

    recipe_content = None
    project_context = None

    with get_session() as session:
        if name:
            proj = session.exec(select(Project).where(Project.name == name)).first()
            if not proj:
                # If project not found in DB, check if it's a special command like 'add-types' (from proposal example)
                # But proposal says "Renders the default recipe of the add-types project". 
                # Meaning add-types should be a project.
                # If not in DB, fail.
                console.print(f"[red]Project '{name}' not found.[/red]")
                return
            if not proj.default_recipe:
                console.print(f"[red]Project '{name}' has no default recipe set.[/red]")
                return
            
            from cli.db.models import Recipe
            rec = session.exec(select(Recipe).where(Recipe.name == proj.default_recipe).where(Recipe.project_id == proj.id)).first()
            if not rec:
                 console.print(f"[red]Default recipe '{proj.default_recipe}' not found in project '{name}'.[/red]")
                 return
            recipe_content = rec.content
            project_context = proj.name
        else:
            # Look for project.json in CWD
            project_json = os.path.join(os.getcwd(), "project.json")
            if not os.path.exists(project_json):
                # Fallback: List all projects if no name and no project.json?
                # Proposal says: "When run with no arguments, it should list all available commands." (for root command)
                # For `kt r` with no args, maybe it tries current dir.
                console.print("[red]No project name provided and project.json not found in current directory.[/red]")
                return
            
            with open(project_json, 'r') as f:
                data = json.load(f)
            
            default_recipe = data.get('default_recipe')
            if not default_recipe:
                console.print("[red]No default recipe specified in project.json[/red]")
                return
            
            # Find recipe in recipes/ folder
            recipe_path = os.path.join(os.getcwd(), "recipes", f"{default_recipe}.lua")
            if not os.path.exists(recipe_path):
                 # Try without .lua
                 recipe_path = os.path.join(os.getcwd(), "recipes", default_recipe)
            
            if not os.path.exists(recipe_path):
                console.print(f"[red]Default recipe file not found: {recipe_path}[/red]")
                return
            
            with open(recipe_path, 'r') as f:
                recipe_content = f.read()
            project_context = data.get('name', 'unbundled')

    if recipe_content:
        context = {}
        if config:
            if not os.path.exists(config):
                console.print(f"[red]Config file '{config}' not found.[/red]")
                return
            context = toml.load(config)
            
        mode = "EXECUTE"
        if create_config and not config:
            mode = "GENERATE_CONFIG"
            
        try:
            engine = RecipeEngine(context=context, mode=mode)
            engine.execute(recipe_content)
            
            if mode == "GENERATE_CONFIG":
                engine.render(create_config)
                console.print(f"[green]Config generated at '{create_config}'[/green]")
            else:
                 console.print(f"[green]Project '{project_context}' rendered using default recipe.[/green]")
        except Exception as e:
            console.print(f"[red]Error rendering project: {e}[/red]")

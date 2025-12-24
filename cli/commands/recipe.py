import click
import os
from rich.console import Console
from rich.table import Table
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Recipe, Project

console = Console()

@click.command("recipe")
@click.argument("name", required=False)
@click.option("--project", help="Project name")
@click.option("--config", help="TOML config file")
@click.option("--create-config", help="Path to create a new config file")
def recipe(name, project, config, create_config):
    """Executes the specified recipe (or lists recipes if no name)."""
    
    with get_session() as session:
        # Project resolution
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id

        if not name:
            # LIST MODE
            query = select(Recipe)
            if project_id:
                query = query.where(Recipe.project_id == project_id)
            else:
                query = query.where(Recipe.project_id == None) # Unassigned only if no project specified? 
                # Or list all?
                # Proposal: "If the project name is specified... executed from that project. Otherwise it will be from the unassigned..."
                # This applies to EXECUTION.
                # For LISTING, usually if no project, maybe list all or unassigned?
                # Existing list command listed unassigned by default.

            recipes = session.exec(query).all()
            
            title = f"Recipes ({project if project else 'Unassigned'})"
            table = Table(title=title)
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Name", style="magenta")
            
            for r in recipes:
                table.add_row(str(r.id), r.name)
                
            console.print(table)
            return

        # EXECUTE MODE
        rec = session.exec(select(Recipe).where(Recipe.name == name).where(Recipe.project_id == project_id)).first()
        if not rec:
             console.print(f"[red]Recipe '{name}' not found{f' in project `{project}`' if project else ''}.[/red]")
             return
             
        # Import engine dependencies
        import toml
        from cli.engine.core import RecipeEngine
        
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
            engine.execute(rec.content)
            
            if mode == "GENERATE_CONFIG":
                engine.render(create_config)
                console.print(f"[green]Config generated at '{create_config}'[/green]")
            else:
                 console.print(f"[green]Recipe '{name}' executed.[/green]")
                 
        except Exception as e:
            console.print(f"[red]Error executing recipe: {e}[/red]")


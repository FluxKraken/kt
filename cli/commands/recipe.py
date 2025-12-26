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
@click.option(
    "--format",
    "config_format",
    type=click.Choice(["toml", "yaml", "yml"], case_sensitive=False),
    default="toml",
    show_default=True,
    help="Config format for generated files",
)
@click.option("--set-default", is_flag=True, help="Set as default recipe for the project")
def recipe(name, project, config, create_config, config_format, set_default):
    """Executes the specified recipe (or lists recipes if no name)."""
    ctx = click.get_current_context()
    format_source = ctx.get_parameter_source("config_format")
    format_specified = format_source == click.core.ParameterSource.COMMANDLINE

    if format_specified and not create_config:
        console.print("[red]--format requires --create-config.[/red]")
        return

    with get_session() as session:
        # Project resolution
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id

        if set_default:
            if not name:
                console.print("[red]Recipe name is required to set as default.[/red]")
                return
            if not project:
                console.print("[red]Project name is required to set a default recipe (--project).[/red]")
                return
            
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                 console.print(f"[red]Project '{project}' not found.[/red]")
                 return
            
            # Verify recipe exists in project?
            # The prompt implies we set it. It doesn't explicitly say we must verify it exists, but it's good practice.
            # However, standard behavior for things like this might permit setting it even if not strictly "assigned" yet?
            # But normally we want it to be valid.
            # Let's check if the recipe exists either assigned or we can assume the user knows.
            # Safest is to check if it exists in the system or project.
            # Implementation plan said: "Update the Project record's default_recipe field."
            
            # Let's verify it exists in the DB first at least
            # Check if execution logic checks for project_id.
            # "rec = session.exec(select(Recipe).where(Recipe.name == name).where(Recipe.project_id == project_id)).first()"
            # If we enforce it must be in the project:
            
            rec = session.exec(select(Recipe).where(Recipe.name == name).where(Recipe.project_id == proj.id)).first()
            if not rec:
                 console.print(f"[red]Recipe '{name}' not found in project '{project}'. Please assign it first.[/red]")
                 return

            proj.default_recipe = name
            session.add(proj)
            session.commit()
            console.print(f"[green]Default recipe for project '{project}' set to '{name}'.[/green]")
            return

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
        if format_specified and mode != "GENERATE_CONFIG":
            console.print("[red]--format is only valid when generating a config file.[/red]")
            return
            
        try:
            engine = RecipeEngine(context=context, mode=mode)
            engine.execute(rec.content)
            
            if mode == "GENERATE_CONFIG":
                if engine.config_template and format_specified:
                    console.print("[red]--format cannot be used when a config template is provided via r.config.[/red]")
                    return
                engine.render(create_config, output_format=config_format)
                console.print(f"[green]Config generated at '{create_config}'[/green]")
            else:
                 console.print(f"[green]Recipe '{name}' executed.[/green]")
                 
        except Exception as e:
            console.print(f"[red]Error executing recipe: {e}[/red]")

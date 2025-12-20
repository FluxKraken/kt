import click
import os

from rich.console import Console
from rich.table import Table
from sqlmodel import select, delete
from cli.db.session import get_session
from cli.db.models import Project

console = Console()

@click.group()
def project():
    """Manage projects"""
    pass

@project.command("list")
def list_projects():
    """List all projects"""
    with get_session() as session:
        projects = session.exec(select(Project)).all()
        
        table = Table(title="Projects")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Created At", justify="right")
        
        for p in projects:
            table.add_row(str(p.id), p.name, str(p.created_at))
            
        console.print(table)

@project.command("add")
@click.argument("name")
def add_project(name):
    """Add a new project"""
    with get_session() as session:
        existing = session.exec(select(Project).where(Project.name == name)).first()
        if existing:
            console.print(f"[red]Project '{name}' already exists.[/red]")
            return
            
        project = Project(name=name)
        session.add(project)
        session.commit()
        console.print(f"[green]Project '{name}' created.[/green]")

@project.command("delete")
@click.argument("name")
@click.option("--recursive", is_flag=True, help="Delete associated templates, recipes, and assets")
def delete_project(name, recursive):
    """Delete a project"""
    with get_session() as session:
        project = session.exec(select(Project).where(Project.name == name)).first()
        if not project:
            console.print(f"[red]Project '{name}' not found.[/red]")
            return
            
        if recursive:
             # Cascading delete is handled by SQLModel/SQLAlchemy if configured, 
             # but we can explicitly ensure it or rely on the relationship definition.
             # In models.py we set cascade_delete=True
             session.delete(project)
             session.commit()
             console.print(f"[green]Project '{name}' and all associated resources deleted.[/green]")
        else:
            # Unassign resources
            for template in project.templates:
                template.project_id = None
                session.add(template)
            for recipe in project.recipes:
                recipe.project_id = None
                session.add(recipe)
            for asset in project.assets:
                asset.project_id = None
                session.add(asset)
            
            session.delete(project)
            session.commit()
            console.print(f"[green]Project '{name}' deleted. Resources unassigned.[/green]")

@project.command("import")
@click.argument("path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing project")
@click.option("--git", is_flag=True, help="Import from a Git repository")
def import_project(path, overwrite, git):
    """Import a project from a bundle (.project), directory, or git repository"""
    from cli.utils.bundler import extract_bundle, import_project_from_dir, import_project_from_git
    try:
        if git:
            import_project_from_git(path, overwrite)
        elif os.path.isdir(path):
            import_project_from_dir(path, overwrite)
        else:
            extract_bundle(path, overwrite)
        console.print(f"[green]Project imported from {'git ' if git else ''}'{path}'.[/green]")
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")

@project.command("export")
@click.argument("name")
@click.option("--output", help="Output file path (.project)")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def export_project(name, output, overwrite):
    """Export a project to a bundle"""
    if not output:
        output = os.path.join(os.getcwd(), f"{name}.project")
        
    from cli.utils.bundler import create_bundle
    try:
        create_bundle(name, output, overwrite)
        console.print(f"[green]Project '{name}' exported to '{output}'.[/green]")
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")

@project.command("default")
@click.argument("name", required=False)
@click.option("--dir", "directory", help="Unbundled project directory")
@click.option("--recipe", required=True, help="Default recipe name")
def set_default_recipe(name, directory, recipe):
    """Set the default recipe for a project"""
    import json
    if directory:
        project_json = os.path.join(directory, "project.json")
        if not os.path.exists(project_json):
            console.print(f"[red]project.json not found in {directory}[/red]")
            return
        with open(project_json, 'r') as f:
            data = json.load(f)
        data['default_recipe'] = recipe
        with open(project_json, 'w') as f:
            json.dump(data, f, indent=4)
        console.print(f"[green]Default recipe set to '{recipe}' in project.json[/green]")
    elif name:
        with get_session() as session:
            proj = session.exec(select(Project).where(Project.name == name)).first()
            if not proj:
                console.print(f"[red]Project '{name}' not found.[/red]")
                return
            proj.default_recipe = recipe
            session.add(proj)
            session.commit()
            console.print(f"[green]Default recipe for project '{name}' set to '{recipe}'.[/green]")
    else:
        console.print("[red]Either project name or --dir must be provided.[/red]")

@project.command("render")
@click.argument("name", required=False)
@click.option("--config", help="TOML config file")
@click.option("--output", help="Output path for generated config")
def render_project(name, config, output):
    """Render the default recipe for a project"""
    import toml
    import json
    from cli.engine.core import RecipeEngine

    recipe_content = None
    project_context = None

    with get_session() as session:
        if name:
            proj = session.exec(select(Project).where(Project.name == name)).first()
            if not proj:
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
        if output and not config:
            mode = "GENERATE_CONFIG"
            
        try:
            engine = RecipeEngine(context=context, mode=mode)
            engine.execute(recipe_content)
            
            if mode == "GENERATE_CONFIG":
                engine.render(output)
                console.print(f"[green]Config generated at '{output}'[/green]")
            else:
                 console.print(f"[green]Project '{project_context}' rendered using default recipe.[/green]")
        except Exception as e:
            console.print(f"[red]Error rendering project: {e}[/red]")

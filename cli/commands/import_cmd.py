import click
import os
from rich.console import Console

console = Console()

@click.command("import")
@click.argument("type_or_path", required=False) # Supporting both "import type ..." and legacy "import path" logic potentially?
# The proposal says: import [type] [identifier]
# or flags like --git, --bundle, --dir
# Actually proposal:
# import [type] [identifier]
# Options: --git, --bundle, --dir, --url
# IMPORTING A PROJECT:
# kt import --git ...
# kt import --bundle ...
# kt import --dir ...
# IMPORTING OTHER TYPES:
# kt import --recipe [name] --file [path] --project [project_name]

# Let's clean this up. The click command structure should probably be:
# kt import [options]
# If we follow the proposal exactly: `kt import [type] [identifier]` seems to be one way, but the examples show `kt import --git ...` which implies options on the main command.
# Let's implement options on the main command.

@click.option("--git", help="Import a project from a Git repository")
@click.option("--bundle", help="Import a project from a bundle (.project)")
@click.option("--dir", "directory", help="Import a project from a directory")
@click.option("--url", help="Import a project from a URL to a bundle") # Not implemented in utils yet?

# Other imports
@click.option("--recipe", help="Import a recipe")
@click.option("--template", help="Import a template")
@click.option("--asset", help="Import an asset")

@click.option("--file", help="File path for resource import")
@click.option("--project", help="Project name to assign imported resource to")

@click.option("--overwrite", is_flag=True, help="Overwrite existing")

def import_cmd(type_or_path, git, bundle, directory, url, recipe, template, asset, file, project, overwrite):
    """Imports a project or resource."""
    from cli.utils.bundler import extract_bundle, import_project_from_dir, import_project_from_git
    from cli.db.session import get_session
    from cli.db.models import Project, Recipe, Template, Asset
    from sqlmodel import select

    # Project Import Logic
    if git:
        try:
            import_project_from_git(git, overwrite)
            console.print(f"[green]Project imported from git '{git}'.[/green]")
        except Exception as e:
            console.print(f"[red]Import failed: {e}[/red]")
        return
    
    if directory:
        try:
            import_project_from_dir(directory, overwrite)
            console.print(f"[green]Project imported from directory '{directory}'.[/green]")
        except Exception as e:
             console.print(f"[red]Import failed: {e}[/red]")
        return

    if bundle or (type_or_path and type_or_path.endswith('.project')):
        path = bundle or type_or_path
        try:
            extract_bundle(path, overwrite)
            console.print(f"[green]Project imported from bundle '{path}'.[/green]")
        except Exception as e:
            console.print(f"[red]Import failed: {e}[/red]")
        return
        
    # Resource Import Logic
    if recipe: # --recipe [name] --file [path]
        if not file:
             console.print("[red]--file is required when importing a recipe.[/red]")
             return
        
        with open(file, 'r') as f:
            content = f.read()
            
        with get_session() as session:
            project_id = None
            if project:
                proj = session.exec(select(Project).where(Project.name == project)).first()
                if not proj:
                    console.print(f"[red]Project '{project}' not found.[/red]")
                    return
                project_id = proj.id
            
            # Check exist
            existing = session.exec(select(Recipe).where(Recipe.name == recipe).where(Recipe.project_id == project_id)).first()
            if existing and not overwrite:
                 console.print(f"[red]Recipe '{recipe}' already exists. Use --overwrite.[/red]")
                 return
            if existing:
                existing.content = content
                session.add(existing)
            else:
                 new_rec = Recipe(name=recipe, project_id=project_id, content=content)
                 session.add(new_rec)
            
            session.commit()
            console.print(f"[green]Recipe '{recipe}' imported.[/green]")
        return

    if template:
        if not file:
             console.print("[red]--file is required when importing a template.[/red]")
             return
        
        with open(file, 'r') as f:
            content = f.read()
            
        with get_session() as session:
            project_id = None
            if project:
                proj = session.exec(select(Project).where(Project.name == project)).first()
                if not proj:
                    console.print(f"[red]Project '{project}' not found.[/red]")
                    return
                project_id = proj.id
            
            existing = session.exec(select(Template).where(Template.name == template).where(Template.project_id == project_id)).first()
            if existing and not overwrite:
                 console.print(f"[red]Template '{template}' already exists. Use --overwrite.[/red]")
                 return
            if existing:
                existing.content = content
                session.add(existing)
            else:
                 new_tmpl = Template(name=template, project_id=project_id, content=content)
                 session.add(new_tmpl)
            
            session.commit()
            console.print(f"[green]Template '{template}' imported.[/green]")
        return

    if asset:
        if not file:
             console.print("[red]--file is required when importing an asset.[/red]")
             return
        
        with open(file, 'rb') as f:
            content = f.read()
            
        with get_session() as session:
            project_id = None
            if project:
                proj = session.exec(select(Project).where(Project.name == project)).first()
                if not proj:
                    console.print(f"[red]Project '{project}' not found.[/red]")
                    return
                project_id = proj.id
            
            existing = session.exec(select(Asset).where(Asset.name == asset).where(Asset.project_id == project_id)).first()
            if existing and not overwrite:
                 console.print(f"[red]Asset '{asset}' already exists. Use --overwrite.[/red]")
                 return
            if existing:
                existing.content = content
                session.add(existing)
            else:
                 new_asset = Asset(name=asset, project_id=project_id, content=content)
                 session.add(new_asset)
            
            session.commit()
            console.print(f"[green]Asset '{asset}' imported.[/green]")
        return

    console.print("[yellow]No import action specified. Use --help for options.[/yellow]")

import click
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
def import_project(path, overwrite):
    """Import a project from a bundle (.project)"""
    from cli.utils.bundler import extract_bundle
    try:
        extract_bundle(path, overwrite)
        console.print(f"[green]Project imported from '{path}'.[/green]")
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")

@project.command("export")
@click.argument("name")
@click.option("--output", required=True, help="Output file path (.project)")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def export_project(name, output, overwrite):
    """Export a project to a bundle"""
    from cli.utils.bundler import create_bundle
    try:
        create_bundle(name, output, overwrite)
        console.print(f"[green]Project '{name}' exported to '{output}'.[/green]")
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")

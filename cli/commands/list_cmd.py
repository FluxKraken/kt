import click
from rich.console import Console
from rich.table import Table
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Project, Recipe, Template, Asset

console = Console()

@click.command("list")
@click.option("--type", required=True, type=click.Choice(['project', 'template', 'recipe', 'asset'], case_sensitive=False), help="Type of resource to list")
@click.option("--project", help="Project name (conflict if type is 'project')")
def list_cmd(type, project):
    """List resources of a specific type."""
    
    if type == 'project':
        if project:
             console.print("[red]Error: --project cannot be used with --type project[/red]")
             return
        
        with get_session() as session:
            projects = session.exec(select(Project)).all()
            
            table = Table(title="Projects")
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Created At", justify="right")
            
            for p in projects:
                table.add_row(str(p.id), p.name, str(p.created_at))
                
            console.print(table)
            return

    # For other types, we need to determine project_id
    with get_session() as session:
        project_id = None
        project_name_display = "Unassigned"
        
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            project_name_display = project
            
        # Select Model based on type
        Model = None
        if type == 'recipe':
            Model = Recipe
        elif type == 'template':
            Model = Template
        elif type == 'asset':
            Model = Asset
            
        query = select(Model)
        if project_id:
             query = query.where(Model.project_id == project_id)
        else:
             query = query.where(Model.project_id == None)
             
        items = session.exec(query).all()
        
        title = f"{type.capitalize()}s ({project_name_display})"
        table = Table(title=title)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="magenta")
        if type == 'asset':
             table.add_column("Source Path", style="dim")
             
        for item in items:
            if type == 'asset':
                table.add_row(str(item.id), item.name, item.source_path)
            else:
                table.add_row(str(item.id), item.name)
                
        console.print(table)

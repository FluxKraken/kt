import click
import os
from rich.console import Console
from rich.table import Table
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Asset, Project

console = Console()

@click.command("asset")
@click.argument("name", required=False)
@click.option("--destination", help="Destination path")
@click.option("--project", help="Project name")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def asset(name, destination, project, overwrite):
    """Copies the specified asset (or lists assets if no name)."""
    
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
            query = select(Asset)
            if project_id:
                query = query.where(Asset.project_id == project_id)
            else:
                query = query.where(Asset.project_id == None)
            
            assets = session.exec(query).all()
            
            title = f"Assets ({project if project else 'Unassigned'})"
            table = Table(title=title)
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Source Path", style="dim")
            
            for a in assets:
                table.add_row(str(a.id), a.name, a.source_path)
                
            console.print(table)
            return

        # COPY MODE
        ast = session.exec(select(Asset).where(Asset.name == name).where(Asset.project_id == project_id)).first()
        if not ast:
             console.print(f"[red]Asset '{name}' not found{f' in project `{project}`' if project else ''}.[/red]")
             return

        if not destination:
             console.print("[red]Error: Missing '--destination'[/red]")
             return
        
        if os.path.exists(destination) and not overwrite:
            console.print(f"[red]Destination file '{destination}' exists. Use --overwrite.[/red]")
            return

        try:
            with open(destination, 'wb') as f:
                f.write(ast.content)
            console.print(f"[green]Asset '{name}' copied to '{destination}'.[/green]")
        except Exception as e:
            console.print(f"[red]Error copying asset: {e}[/red]")


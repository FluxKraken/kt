import click
import os
from rich.console import Console
from rich.table import Table
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Asset, Project

console = Console()

@click.group()
def asset():
    """Manage assets"""
    pass

@asset.command("list")
@click.option("--project", help="Project name to filter by")
def list_assets(project):
    """List assets"""
    with get_session() as session:
        query = select(Asset)
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            query = query.where(Asset.project_id == proj.id)
        else:
            query = query.where(Asset.project_id == None)
            
        assets = session.exec(query).all()
        
        table = Table(title=f"Assets ({project if project else 'Unassigned'})")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Source Path", style="dim")
        
        for a in assets:
            table.add_row(str(a.id), a.name, a.source_path)
            
        console.print(table)

@asset.command("add")
@click.argument("name")
@click.option("--file", required=True, help="File path to asset")
@click.option("--project", help="Project to assign to")
def add_asset(name, file, project):
    """Add a new asset from file"""
    if not os.path.exists(file):
        console.print(f"[red]File '{file}' not found.[/red]")
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
            
        # Check if exists
        existing_query = select(Asset).where(Asset.name == name).where(Asset.project_id == project_id)
        existing = session.exec(existing_query).first()
        if existing:
            console.print(f"[red]Asset '{name}' already exists in this context. Use delete first.[/red]")
            return

        asset_obj = Asset(name=name, source_path=file, content=content, project_id=project_id)
        session.add(asset_obj)
        session.commit()
        console.print(f"[green]Asset '{name}' added.[/green]")

@asset.command("delete")
@click.argument("name")
@click.option("--project", help="Project context")
def delete_asset(name, project):
    """Delete an asset"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id

        asset_obj = session.exec(select(Asset).where(Asset.name == name).where(Asset.project_id == project_id)).first()
        if not asset_obj:
            console.print(f"[red]Asset '{name}' not found.[/red]")
            return
            
        session.delete(asset_obj)
        session.commit()
        console.print(f"[green]Asset '{name}' deleted.[/green]")

@asset.command("assign")
@click.argument("name")
@click.option("--project", help="Project to assign to", required=True)
@click.option("--copy", is_flag=True, help="Copy instead of move")
def assign_asset(name, project, copy):
    """Assign an asset to a project"""
    with get_session() as session:
        # Find the project
        proj = session.exec(select(Project).where(Project.name == project)).first()
        if not proj:
            console.print(f"[red]Project '{project}' not found.[/red]")
            return
        
        # Find the asset (prefer unassigned)
        asset_obj = session.exec(select(Asset).where(Asset.name == name).where(Asset.project_id == None)).first()
        
        if not asset_obj:
             assets = session.exec(select(Asset).where(Asset.name == name)).all()
             if not assets:
                 console.print(f"[red]Asset '{name}' not found.[/red]")
                 return
             if len(assets) > 1:
                 console.print(f"[red]Multiple assets named '{name}' found. Please create a unique name.[/red]")
                 return
             asset_obj = assets[0]
        
        if asset_obj.project_id == proj.id:
            console.print(f"[yellow]Asset '{name}' is already assigned to project '{project}'.[/yellow]")
            return

        # Check if destination already has an asset with this name
        existing = session.exec(select(Asset).where(Asset.name == name).where(Asset.project_id == proj.id)).first()
        if existing:
            console.print(f"[red]Project '{project}' already has an asset named '{name}'.[/red]")
            return

        if copy:
            new_asset = Asset(name=asset_obj.name, source_path=asset_obj.source_path, content=asset_obj.content, project_id=proj.id)
            session.add(new_asset)
            console.print(f"[green]Asset '{name}' copied to project '{project}'.[/green]")
        else:
            asset_obj.project_id = proj.id
            session.add(asset_obj)
            console.print(f"[green]Asset '{name}' moved to project '{project}'.[/green]")
            
        session.commit()

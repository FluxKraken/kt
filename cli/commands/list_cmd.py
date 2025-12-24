import click
from rich.console import Console
from rich.table import Table
from sqlmodel import select, func
from cli.db.session import get_session
from cli.db.models import Project, Recipe, Template, Asset

console = Console()

@click.command("list")
@click.option("--type", required=False, type=click.Choice(['project', 'template', 'recipe', 'asset'], case_sensitive=False), help="Type of resource to list")
@click.option("--project", help="Project name (conflict if type is 'project')")
def list_cmd(type, project):
    """List resources of a specific type or show a summary of all resources."""
    
    # If no type is provided, show the summary view
    if not type:
        if project:
            console.print("[red]Error: --project cannot be used without --type[/red]")
            return
            
        with get_session() as session:
            # 1. Unassigned Recipes
            unassigned_recipes = session.exec(select(Recipe).where(Recipe.project_id == None)).all()
            
            # 2. Unassigned Templates
            unassigned_templates = session.exec(select(Template).where(Template.project_id == None)).all()
            
            # 3. Unassigned Assets
            unassigned_assets = session.exec(select(Asset).where(Asset.project_id == None)).all()
            
            # 4. Projects with counts
            # We fetch all projects and manually count for now to be simple and safe with SQLModel relationships
            # Alternatively, we could do a joined query, but iterating is fine for reasonable datasets
            projects = session.exec(select(Project)).all()
            
            # Display Unassigned Recipes
            if unassigned_recipes:
                table = Table(title="Unassigned Recipes", show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim", width=4)
                table.add_column("Name")
                for r in unassigned_recipes:
                    table.add_row(str(r.id), r.name)
                console.print(table)
                console.print()
            else:
                 console.print("[dim]No unassigned recipes[/dim]")
                 console.print()

            # Display Unassigned Templates
            if unassigned_templates:
                table = Table(title="Unassigned Templates", show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim", width=4)
                table.add_column("Name")
                for t in unassigned_templates:
                    table.add_row(str(t.id), t.name)
                console.print(table)
                console.print()
            else:
                 console.print("[dim]No unassigned templates[/dim]")
                 console.print()

            # Display Unassigned Assets
            if unassigned_assets:
                table = Table(title="Unassigned Assets", show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim", width=4)
                table.add_column("Name")
                table.add_column("Source Path", style="dim")
                for a in unassigned_assets:
                    table.add_row(str(a.id), a.name, a.source_path)
                console.print(table)
                console.print()
            else:
                 console.print("[dim]No unassigned assets[/dim]")
                 console.print()

            # Display Projects
            if projects:
                table = Table(title="Projects", show_header=True, header_style="bold blue")
                table.add_column("ID", style="dim", width=4)
                table.add_column("Name", style="bold")
                table.add_column("Recipes", justify="right")
                table.add_column("Templates", justify="right")
                table.add_column("Assets", justify="right")
                
                for p in projects:
                    # Using the relationships defined in models.py
                    r_count = len(p.recipes)
                    t_count = len(p.templates)
                    a_count = len(p.assets)
                    table.add_row(str(p.id), p.name, str(r_count), str(t_count), str(a_count))
                console.print(table)
            else:
                console.print("[dim]No projects found[/dim]")
                
        return

    # EXISTING LOGIC FOR SPECIFIC TYPE LISTING
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

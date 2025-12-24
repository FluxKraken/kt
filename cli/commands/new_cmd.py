import click
from rich.console import Console
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Project, Recipe, Template, Asset

console = Console()

@click.command("new")
@click.option("--project", help="Project name (for project creation or assignment)")
@click.option("--recipe", help="Recipe name to create")
@click.option("--template", help="Template name to create")
@click.option("--asset", help="Asset name to create")
def new_cmd(project, recipe, template, asset):
    """Creates a new object of the specified type."""
    # Proposal:
    # new --[type] [name] --project [project_name]
    # --project [project_name]  -> Creates project if others not specified?
    # --recipe [name] --project [project_name]
    
    with get_session() as session:
        if project and not any([recipe, template, asset]):
            # Create Project
            existing = session.exec(select(Project).where(Project.name == project)).first()
            if existing:
                console.print(f"[red]Project '{project}' already exists.[/red]")
                return
            
            p = Project(name=project)
            session.add(p)
            session.commit()
            console.print(f"[green]Project '{project}' created.[/green]")
            return

        # Resource Creation
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id

        if recipe:
            # Check exist
            existing = session.exec(select(Recipe).where(Recipe.name == recipe).where(Recipe.project_id == project_id)).first()
            if existing:
                console.print(f"[red]Recipe '{recipe}' already exists.[/red]")
            else:
                rec = Recipe(name=recipe, content="", project_id=project_id)
                session.add(rec)
                session.commit()
                console.print(f"[green]Recipe '{recipe}' created.[/green]")
        
        if template:
            existing = session.exec(select(Template).where(Template.name == template).where(Template.project_id == project_id)).first()
            if existing:
                console.print(f"[red]Template '{template}' already exists.[/red]")
            else:
                tmpl = Template(name=template, content="", project_id=project_id)
                session.add(tmpl)
                session.commit()
                console.print(f"[green]Template '{template}' created.[/green]")
                
        if asset:
            existing = session.exec(select(Asset).where(Asset.name == asset).where(Asset.project_id == project_id)).first()
            if existing:
                console.print(f"[red]Asset '{asset}' already exists.[/red]")
            else:
                # Assets usually need file content. KT NEW implies empty or created from... what? 
                # Proposal doesn't specify source file for NEW command, only for IMPORT / ASSET ADD.
                # Assuming empty asset placeholder? Or maybe assets can't be "created" like this without file?
                # User request says "new --asset [name]".
                ast = Asset(name=asset, content=b"", project_id=project_id)
                session.add(ast)
                session.commit()
                console.print(f"[green]Asset '{asset}' created (empty).[/green]")

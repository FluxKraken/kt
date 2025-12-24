import click
from rich.console import Console
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Project, Recipe, Template, Asset

console = Console()

@click.command("assign")
@click.option("--recipe", help="Recipe name")
@click.option("--template", help="Template name")
@click.option("--asset", help="Asset name")
@click.option("--project", required=True, help="Target project name")
def assign_cmd(recipe, template, asset, project):
    """Assigns the specified object to the specified project."""
    with get_session() as session:
        proj = session.exec(select(Project).where(Project.name == project)).first()
        if not proj:
            console.print(f"[red]Project '{project}' not found.[/red]")
            return

        if recipe:
            # logic to find recipe (unassigned or from another project?)
            # Assuming we can find by name globally or we need to know where it is.
            # If name is unique globally:
            rec = session.exec(select(Recipe).where(Recipe.name == recipe)).first()
            if rec:
                rec.project_id = proj.id
                session.add(rec)
                console.print(f"[green]Recipe '{recipe}' assigned to '{project}'.[/green]")
            else:
                console.print(f"[red]Recipe '{recipe}' not found.[/red]")
        
        if template:
            tmpl = session.exec(select(Template).where(Template.name == template)).first()
            if tmpl:
                tmpl.project_id = proj.id
                session.add(tmpl)
                console.print(f"[green]Template '{template}' assigned to '{project}'.[/green]")
            else:
                console.print(f"[red]Template '{template}' not found.[/red]")

        if asset:
            ast = session.exec(select(Asset).where(Asset.name == asset)).first()
            if ast:
                ast.project_id = proj.id
                session.add(ast)
                console.print(f"[green]Asset '{asset}' assigned to '{project}'.[/green]")
            else:
                console.print(f"[red]Asset '{asset}' not found.[/red]")

        session.commit()

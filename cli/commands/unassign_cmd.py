import click
from rich.console import Console
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Project, Recipe, Template, Asset

console = Console()

@click.command("unassign")
@click.option("--recipe", help="Recipe name")
@click.option("--template", help="Template name")
@click.option("--asset", help="Asset name")
@click.option("--project", required=True, help="Target project name")
def unassign_cmd(recipe, template, asset, project):
    """Unassigns the specified object from the specified project."""
    if not any([recipe, template, asset]):
        console.print("[red]Please specify at least one resource to unassign (--recipe, --template, or --asset).[/red]")
        return

    with get_session() as session:
        proj = session.exec(select(Project).where(Project.name == project)).first()
        if not proj:
            console.print(f"[red]Project '{project}' not found.[/red]")
            return

        if recipe:
            rec = session.exec(select(Recipe).where(Recipe.name == recipe).where(Recipe.project_id == proj.id)).first()
            if rec:
                rec.project_id = None
                session.add(rec)
                console.print(f"[green]Recipe '{recipe}' unassigned from '{project}'.[/green]")
            else:
                console.print(f"[red]Recipe '{recipe}' not found in project '{project}'.[/red]")
        
        if template:
            tmpl = session.exec(select(Template).where(Template.name == template).where(Template.project_id == proj.id)).first()
            if tmpl:
                tmpl.project_id = None
                session.add(tmpl)
                console.print(f"[green]Template '{template}' unassigned from '{project}'.[/green]")
            else:
                 console.print(f"[red]Template '{template}' not found in project '{project}'.[/red]")

        if asset:
            ast = session.exec(select(Asset).where(Asset.name == asset).where(Asset.project_id == proj.id)).first()
            if ast:
                ast.project_id = None
                session.add(ast)
                console.print(f"[green]Asset '{asset}' unassigned from '{project}'.[/green]")
            else:
                console.print(f"[red]Asset '{asset}' not found in project '{project}'.[/red]")

        session.commit()

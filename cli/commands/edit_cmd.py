import click
from rich.console import Console
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Project, Recipe, Template

console = Console()

@click.command("edit")
@click.option("--recipe", help="Recipe name to edit")
@click.option("--template", help="Template name to edit")
@click.option("--project", help="Project name where the resource is located")
def edit_cmd(recipe, template, project):
    """Edits an existing object of the specified type using the default editor."""
    
    if not any([recipe, template]):
         console.print("[red]Please specify --recipe or --template to edit.[/red]")
         return

    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id

        if recipe:
            rec = session.exec(select(Recipe).where(Recipe.name == recipe).where(Recipe.project_id == project_id)).first()
            if not rec:
                console.print(f"[red]Recipe '{recipe}' not found{f' in project `{project}`' if project else ''}.[/red]")
                return
            
            new_content = click.edit(rec.content)
            if new_content is not None:
                rec.content = new_content
                session.add(rec)
                session.commit()
                console.print(f"[green]Recipe '{recipe}' updated.[/green]")
            else:
                console.print("[yellow]No changes made.[/yellow]")

        if template:
            tmpl = session.exec(select(Template).where(Template.name == template).where(Template.project_id == project_id)).first()
            if not tmpl:
                console.print(f"[red]Template '{template}' not found{f' in project `{project}`' if project else ''}.[/red]")
                return
            
            new_content = click.edit(tmpl.content)
            if new_content is not None:
                tmpl.content = new_content
                session.add(tmpl)
                session.commit()
                console.print(f"[green]Template '{template}' updated.[/green]")
            else:
                 console.print("[yellow]No changes made.[/yellow]")

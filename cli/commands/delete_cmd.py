import click
from rich.console import Console
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Project, Recipe, Template, Asset

console = Console()

@click.command("delete")
@click.option("--recipe", help="Recipe name")
@click.option("--template", help="Template name")
@click.option("--asset", help="Asset name")
@click.option("--project", help="Project name")
@click.option("--recursive", is_flag=True, help="Recursive delete (for project)")
def delete_cmd(recipe, template, asset, project, recursive):
    """Deletes the specified object."""
    # Proposal:
    # delete --[type] [name] --project [project_name] --recursive
    # "In the case of type --project, the specified project will be deleted... In the case of name conflicts..."
    # "If the recursive flag is specified, the project will be deleted recursively..."

    # If --project is specified alone (without recipe/template/asset), it means delete the project?
    # Or is --project an argument for WHERE the recipe/template/asset is?
    # Example: --recipe foo --project bar (Delete recipe foo from project bar? Or delete recipe foo which is IN project bar?)
    # "Deletes the specified object from the specified project." implies checking project scope.

    with get_session() as session:
        
        if project and not any([recipe, template, asset]):
            # Delete Project
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            
            if recursive:
                 session.delete(proj)
                 session.commit()
                 console.print(f"[green]Project '{project}' and all associated resources deleted.[/green]")
            else:
                # Unassign resources
                for r in proj.recipes:
                    r.project_id = None
                    session.add(r)
                for t in proj.templates:
                    t.project_id = None
                    session.add(t)
                for a in proj.assets:
                    a.project_id = None
                    session.add(a)
                session.commit()
                
                session.delete(proj)
                session.commit()
                console.print(f"[green]Project '{project}' deleted. Resources unassigned.[/green]")
            return

        # Resource Deletion
        
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                 console.print(f"[red]Project '{project}' not found.[/red]")
                 return
            project_id = proj.id

        if recipe:
            query = select(Recipe).where(Recipe.name == recipe)
            if project_id:
                query = query.where(Recipe.project_id == project_id)
            
            # If we don't have project_id, what if there are duplicates?
            # Proposal doesn't explicitly handle unassigned vs global conflict here except mentioning "name conflicts" for project deletion?
            # Let's assume name is unique or we need to be specific.
            
            recs = session.exec(query).all()
            if not recs:
                console.print(f"[red]Recipe '{recipe}' not found{f' in project `{project}`' if project else ''}.[/red]")
            else:
                 for r in recs:
                     session.delete(r)
                 session.commit()
                 console.print(f"[green]Recipe '{recipe}' deleted.[/green]")

        if template:
            query = select(Template).where(Template.name == template)
            if project_id:
                query = query.where(Template.project_id == project_id)
            
            tmpls = session.exec(query).all()
            if not tmpls:
                 console.print(f"[red]Template '{template}' not found{f' in project `{project}`' if project else ''}.[/red]")
            else:
                 for t in tmpls:
                     session.delete(t)
                 session.commit()
                 console.print(f"[green]Template '{template}' deleted.[/green]")

        if asset:
            query = select(Asset).where(Asset.name == asset)
            if project_id:
                query = query.where(Asset.project_id == project_id)
            
            asts = session.exec(query).all()
            if not asts:
                 console.print(f"[red]Asset '{asset}' not found{f' in project `{project}`' if project else ''}.[/red]")
            else:
                 for a in asts:
                     session.delete(a)
                 session.commit()
                 console.print(f"[green]Asset '{asset}' deleted.[/green]")

import click
import os
from rich.console import Console
from rich.table import Table
from sqlmodel import select
from cli.db.session import get_session
from cli.db.models import Recipe, Project

console = Console()

@click.group()
def recipe():
    """Manage recipes"""
    pass

@recipe.command("list")
@click.option("--project", help="Project name to filter by")
def list_recipes(project):
    """List recipes"""
    with get_session() as session:
        query = select(Recipe)
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            query = query.where(Recipe.project_id == proj.id)
        else:
            query = query.where(Recipe.project_id == None)
            
        recipes = session.exec(query).all()
        
        table = Table(title=f"Recipes ({project if project else 'Unassigned'})")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="magenta")
        
        for r in recipes:
            table.add_row(str(r.id), r.name)
            
        console.print(table)

@recipe.command("add")
@click.argument("name")
@click.option("--project", help="Project to assign to")
def add_recipe(name, project):
    """Add a new recipe (opens editor)"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        existing_query = select(Recipe).where(Recipe.name == name).where(Recipe.project_id == project_id)
        existing = session.exec(existing_query).first()
        if existing:
            console.print(f"[red]Recipe '{name}' already exists in this context.[/red]")
            return

        content = click.edit("-- Recipe: " + name)
        if content is None:
            console.print("[yellow]No content provided. Aborting.[/yellow]")
            return
            
        rec = Recipe(name=name, content=content, project_id=project_id)
        session.add(rec)
        session.commit()
        console.print(f"[green]Recipe '{name}' added.[/green]")

@recipe.command("edit")
@click.argument("name")
@click.option("--project", help="Project context")
def edit_recipe(name, project):
    """Edit an existing recipe"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        rec = session.exec(select(Recipe).where(Recipe.name == name).where(Recipe.project_id == project_id)).first()
        if not rec:
            console.print(f"[red]Recipe '{name}' not found.[/red]")
            return
            
        new_content = click.edit(rec.content)
        if new_content is not None:
            rec.content = new_content
            session.add(rec)
            session.commit()
            console.print(f"[green]Recipe '{name}' updated.[/green]")

@recipe.command("delete")
@click.argument("name")
@click.option("--project", help="Project context")
def delete_recipe(name, project):
    """Delete a recipe"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id

        rec = session.exec(select(Recipe).where(Recipe.name == name).where(Recipe.project_id == project_id)).first()
        if not rec:
            console.print(f"[red]Recipe '{name}' not found.[/red]")
            return
            
        session.delete(rec)
        session.commit()
        console.print(f"[green]Recipe '{name}' deleted.[/green]")

@recipe.command("import")
@click.argument("path")
@click.option("--project", help="Project context")
@click.option("--name", help="Recipe name (default: filename)")
@click.option("--overwrite", is_flag=True)
def import_recipe(path, project, name, overwrite):
    """Import a file as a recipe"""
    if not os.path.exists(path):
        console.print(f"[red]File '{path}' not found.[/red]")
        return
        
    recipe_name = name or os.path.splitext(os.path.basename(path))[0]
    
    with open(path, 'r') as f:
        content = f.read()
        
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        existing = session.exec(select(Recipe).where(Recipe.name == recipe_name).where(Recipe.project_id == project_id)).first()
        if existing:
            if not overwrite:
                 console.print(f"[red]Recipe '{recipe_name}' already exists. Use --overwrite.[/red]")
                 return
            existing.content = content
            session.add(existing)
            console.print(f"[green]Recipe '{recipe_name}' updated.[/green]")
        else:
            rec = Recipe(name=recipe_name, content=content, project_id=project_id)
            session.add(rec)
            console.print(f"[green]Recipe '{recipe_name}' imported.[/green]")
        
        session.commit()

@recipe.command("export")
@click.argument("name")
@click.option("--project", help="Project context")
@click.option("--output", help="Output file path", required=True)
@click.option("--overwrite", is_flag=True)
def export_recipe(name, project, output, overwrite):
    """Export a recipe to a file"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        rec = session.exec(select(Recipe).where(Recipe.name == name).where(Recipe.project_id == project_id)).first()
        if not rec:
            console.print(f"[red]Recipe '{name}' not found.[/red]")
            return

        if os.path.exists(output) and not overwrite:
            console.print(f"[red]Output file '{output}' exists. Use --overwrite.[/red]")
            return
            
        with open(output, 'w') as f:
            f.write(rec.content)
        console.print(f"[green]Recipe exported to '{output}'.[/green]")

@recipe.command("render")
@click.argument("name")
@click.option("--project", help="Project context")
@click.option("--config", help="TOML config file")
@click.option("--output", help="Output path for generated config (if no config provided)")
def render_recipe(name, project, config, output):
    """Render and execute a recipe"""
    import toml
    from cli.engine.core import RecipeEngine
    
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        rec = session.exec(select(Recipe).where(Recipe.name == name).where(Recipe.project_id == project_id)).first()
        if not rec:
            console.print(f"[red]Recipe '{name}' not found.[/red]")
            return
            
        context = {}
        if config:
            if not os.path.exists(config):
                console.print(f"[red]Config file '{config}' not found.[/red]")
                return
            context = toml.load(config)
            
        mode = "EXECUTE"
        if output and not config:
            mode = "GENERATE_CONFIG"
            
        try:
            engine = RecipeEngine(context=context, mode=mode)
            engine.execute(rec.content)
            
            if mode == "GENERATE_CONFIG":
                # Filter context to only show what was explicitly prompted
                # collected_prompts has the structure of defaults.
                # We want to use values from engine.context if they exist, but only keys from collected_prompts.
                
                from collections import OrderedDict
                final_output = OrderedDict()
                
                def deep_filter(mask, source):
                    result = OrderedDict()
                    for k, v in mask.items():
                        if isinstance(v, dict):
                            if k in source and isinstance(source[k], dict):
                                nested = deep_filter(v, source[k])
                                if nested:
                                    result[k] = nested
                        else:
                            # Leaf
                            if k in source:
                                result[k] = source[k]
                            else:
                                result[k] = v
                    return result

                final_output = deep_filter(engine.actions.collected_prompts, engine.context)

                with open(output, 'w') as f:
                    toml.dump(final_output, f)
                console.print(f"[green]Config generated at '{output}'[/green]")
            else:
                 console.print(f"[green]Recipe '{name}' executed.[/green]")
                 
        except Exception as e:
            console.print(f"[red]Error executing recipe: {e}[/red]")

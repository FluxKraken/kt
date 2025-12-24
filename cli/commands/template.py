import click
import os
from rich.console import Console
from rich.table import Table
from sqlmodel import select
from jinja2 import Template as JinjaTemplate
from cli.db.session import get_session
from cli.db.models import Template, Project

console = Console()

@click.command("template")
@click.argument("name", required=False)
@click.option("--destination", help="Destination path for rendered template")
@click.option("--project", help="Project name")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@click.option("--config", help="TOML config file")
@click.option("--create-config", help="Path to create a new config file")
def template(name, destination, project, overwrite, config, create_config):
    """Renders the specified template (or lists templates if no name)."""
    
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
            query = select(Template)
            if project_id:
                query = query.where(Template.project_id == project_id)
            else:
                query = query.where(Template.project_id == None)
            
            templates = session.exec(query).all()
            
            title = f"Templates ({project if project else 'Unassigned'})"
            table = Table(title=title)
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Name", style="magenta")
            
            for t in templates:
                table.add_row(str(t.id), t.name)
                
            console.print(table)
            return

        # RENDER MODE
        tmpl = session.exec(select(Template).where(Template.name == name).where(Template.project_id == project_id)).first()
        if not tmpl:
             console.print(f"[red]Template '{name}' not found{f' in project `{project}`' if project else ''}.[/red]")
             return
        
        # logic for rendering
        import json
        import toml
        from cli.engine.jinja_utils import (
            extract_nested_variables, 
            render_template_with_shell,
            merge_recursive,
            check_missing
        )
        
        # Parse template
        try:
            skeleton = extract_nested_variables(tmpl.content)
        except Exception as e:
            console.print(f"[red]Error parsing template: {e}[/red]")
            return

        # Create Config Only
        if create_config:
            if os.path.exists(create_config) and not overwrite:
                console.print(f"[red]Output file '{create_config}' exists. Use --overwrite.[/red]")
                return
            
            with open(create_config, 'w') as f:
                toml.dump(skeleton, f)
            console.print(f"[green]Config skeleton generated at '{create_config}'.[/green]")
            return

        if not destination:
             console.print("[red]Error: Missing '--destination' (or '--create-config')[/red]")
             return

        if os.path.exists(destination) and not overwrite:
            console.print(f"[red]Destination file '{destination}' exists. Use --overwrite.[/red]")
            return
            
        context = {}
        if config:
            if not os.path.exists(config):
                console.print(f"[red]Config file '{config}' not found.[/red]")
                return
            context = toml.load(config)
            
        if skeleton:
             missing_any = check_missing(skeleton, context)
             if missing_any:
                console.print("[yellow]Template variables are missing. Opening editor...[/yellow]")
                prompt_data = skeleton.copy()
                merge_recursive(prompt_data, context)
                
                header = f"# Fill in missing variables for template '{name}'\n"
                toml_str = toml.dumps(prompt_data)
                
                new_toml = click.edit(header + toml_str, extension=".toml")
                if new_toml is None:
                    console.print("[red]Render cancelled by user.[/red]")
                    return
                
                try:
                    new_data = toml.loads(new_toml)
                    merge_recursive(context, new_data)
                except Exception as e:
                    console.print(f"[red]Error parsing input: {e}[/red]")
                    return

        try:
            rendered = render_template_with_shell(tmpl.content, context)
            
            with open(destination, 'w') as f:
                f.write(rendered)
            console.print(f"[green]Template rendered to '{destination}'.[/green]")
        except Exception as e:
            console.print(f"[red]Error rendering template: {e}[/red]")


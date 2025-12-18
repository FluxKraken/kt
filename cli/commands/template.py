import click
import os
from rich.console import Console
from rich.table import Table
from sqlmodel import select
from jinja2 import Template as JinjaTemplate
from cli.db.session import get_session
from cli.db.models import Template, Project

console = Console()

@click.group()
def template():
    """Manage templates"""
    pass

@template.command("list")
@click.option("--project", help="Project name to filter by")
def list_templates(project):
    """List templates"""
    with get_session() as session:
        query = select(Template)
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            query = query.where(Template.project_id == proj.id)
        else:
            query = query.where(Template.project_id == None)
            
        templates = session.exec(query).all()
        
        table = Table(title=f"Templates ({project if project else 'Unassigned'})")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="magenta")
        
        for t in templates:
            table.add_row(str(t.id), t.name)
            
        console.print(table)

@template.command("add")
@click.argument("name")
@click.option("--project", help="Project to assign to")
def add_template(name, project):
    """Add a new template (opens editor)"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        # Check if exists
        existing_query = select(Template).where(Template.name == name).where(Template.project_id == project_id)
        existing = session.exec(existing_query).first()
        if existing:
            console.print(f"[red]Template '{name}' already exists in this context.[/red]")
            return

        content = click.edit("")
        if content is None:
            console.print("[yellow]No content provided. Aborting.[/yellow]")
            return
            
        tmpl = Template(name=name, content=content, project_id=project_id)
        session.add(tmpl)
        session.commit()
        console.print(f"[green]Template '{name}' added.[/green]")

@template.command("edit")
@click.argument("name")
@click.option("--project", help="Project context")
def edit_template(name, project):
    """Edit an existing template"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        tmpl = session.exec(select(Template).where(Template.name == name).where(Template.project_id == project_id)).first()
        if not tmpl:
            console.print(f"[red]Template '{name}' not found.[/red]")
            return
            
        new_content = click.edit(tmpl.content)
        if new_content is not None:
            tmpl.content = new_content
            session.add(tmpl)
            session.commit()
            console.print(f"[green]Template '{name}' updated.[/green]")

@template.command("delete")
@click.argument("name")
@click.option("--project", help="Project context")
def delete_template(name, project):
    """Delete a template"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id

        tmpl = session.exec(select(Template).where(Template.name == name).where(Template.project_id == project_id)).first()
        if not tmpl:
            console.print(f"[red]Template '{name}' not found.[/red]")
            return
            
        session.delete(tmpl)
        session.commit()
        console.print(f"[green]Template '{name}' deleted.[/green]")

@template.command("render")
@click.argument("name")
@click.option("--project", help="Project context")
@click.option("--output", help="Output file path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@click.option("--config", help="TOML config file")
@click.option("--gen-config", help="Generate config file skeleton path")
def render_template(name, project, output, overwrite, config, gen_config):
    """Render a template to a file"""
    import json
    import toml
    from jinja2 import Environment
    from cli.engine.jinja_utils import (
        extract_nested_variables, 
        render_template_with_shell,
        merge_recursive,
        check_missing
    )
    
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        tmpl = session.exec(select(Template).where(Template.name == name).where(Template.project_id == project_id)).first()
        if not tmpl:
            console.print(f"[red]Template '{name}' not found.[/red]")
            return

        # Parse template to find variables (including nested ones)
        try:
            skeleton = extract_nested_variables(tmpl.content)
        except Exception as e:
            console.print(f"[red]Error parsing template: {e}[/red]")
            return

        # Gen Config Mode
        if gen_config:
            if os.path.exists(gen_config) and not overwrite:
                console.print(f"[red]Output file '{gen_config}' exists. Use --overwrite.[/red]")
                return
            
            with open(gen_config, 'w') as f:
                toml.dump(skeleton, f)
            console.print(f"[green]Config skeleton generated at '{gen_config}'.[/green]")
            return

        # Render Mode requirements
        if not output:
             console.print("[red]Error: Missing '--output' (or '--gen-config')[/red]")
             return

        if os.path.exists(output) and not overwrite:
            console.print(f"[red]Output file '{output}' exists. Use --overwrite.[/red]")
            return
            
        # Load Context
        context = {}
        if config:
            if not os.path.exists(config):
                console.print(f"[red]Config file '{config}' not found.[/red]")
                return
            context = toml.load(config)
            
        # Identify missing variables (at top level for simple check, but we'll prompt for all if any missing)
        # For simplicity, we check if any keys in skeleton are missing in context.
        # However, it's better to just merge context into skeleton and see what's left as empty.
        
        if skeleton:
             # Check if we have all variables
             missing_any = check_missing(skeleton, context)

             if missing_any:
                console.print("[yellow]Template variables are missing. Opening editor...[/yellow]")
                
                # Merge existing context into skeleton to show current values
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
            
            with open(output, 'w') as f:
                f.write(rendered)
            console.print(f"[green]Template rendered to '{output}'.[/green]")
        except Exception as e:
            console.print(f"[red]Error rendering template: {e}[/red]")

@template.command("import")
@click.argument("path")
@click.option("--project", help="Project context")
@click.option("--name", help="Template name (default: filename)")
@click.option("--overwrite", is_flag=True)
def import_template(path, project, name, overwrite):
    """Import a file as a template"""
    if not os.path.exists(path):
        console.print(f"[red]File '{path}' not found.[/red]")
        return
        
    template_name = name or os.path.basename(path)
    
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
            
        existing = session.exec(select(Template).where(Template.name == template_name).where(Template.project_id == project_id)).first()
        if existing:
            if not overwrite:
                 console.print(f"[red]Template '{template_name}' already exists. Use --overwrite.[/red]")
                 return
            existing.content = content
            session.add(existing)
            console.print(f"[green]Template '{template_name}' updated.[/green]")
        else:
            tmpl = Template(name=template_name, content=content, project_id=project_id)
            session.add(tmpl)
            console.print(f"[green]Template '{template_name}' imported.[/green]")
        
        session.commit()

@template.command("export")
@click.argument("name")
@click.option("--project", help="Project context")
@click.option("--output", help="Output file path", required=True)
@click.option("--overwrite", is_flag=True)
def export_template(name, project, output, overwrite):
    """Export a template to a file"""
    with get_session() as session:
        project_id = None
        if project:
            proj = session.exec(select(Project).where(Project.name == project)).first()
            if not proj:
                console.print(f"[red]Project '{project}' not found.[/red]")
                return
            project_id = proj.id
            
        tmpl = session.exec(select(Template).where(Template.name == name).where(Template.project_id == project_id)).first()
        if not tmpl:
            console.print(f"[red]Template '{name}' not found.[/red]")
            return

        if os.path.exists(output) and not overwrite:
            console.print(f"[red]Output file '{output}' exists. Use --overwrite.[/red]")
            return
            
        with open(output, 'w') as f:
            f.write(tmpl.content)
        console.print(f"[green]Template exported to '{output}'.[/green]")

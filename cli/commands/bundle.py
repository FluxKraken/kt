import click
import os
import json
from rich.console import Console
from cli.utils.bundler import expand_bundle_to_path, bundle_path_to_archive, init_bundle_structure

console = Console()

@click.group()
def bundle():
    """Bundle projects to/from .project archives"""
    pass

@bundle.command("init")
@click.argument("path", default=".")
def init(path):
    """Initialize a project bundle structure"""
    try:
        init_bundle_structure(path)
        console.print(f"[green]Successfully initialized bundle project at '{path}'.[/green]")
    except Exception as e:
        console.print(f"[red]Error initializing bundle project: {e}[/red]")

@bundle.command("expand")
@click.argument("bundle_path")
@click.argument("extract_path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files")
def expand(bundle_path, extract_path, overwrite):
    """Expand a .project archive to a path"""
    try:
        expand_bundle_to_path(bundle_path, extract_path, overwrite)
        console.print(f"[green]Successfully expanded '{bundle_path}' to '{extract_path}'.[/green]")
    except Exception as e:
        console.print(f"[red]Error expanding bundle: {e}[/red]")

@bundle.command("create")
@click.argument("source_path", default=".")
@click.option("-f", "--file", "output_path", help="Output .project file path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def create(source_path, output_path, overwrite):
    """Create a .project archive from a path"""
    try:
        if not output_path:
            # Default output path is cwd / project_name.project
            # Get project name from project.json if exists
            proj_json = os.path.join(source_path, "project.json")
            if os.path.exists(proj_json):
                with open(proj_json, 'r') as f:
                    meta = json.load(f)
                    project_name = meta.get("name")
            else:
                project_name = os.path.basename(os.path.abspath(source_path))
            
            if not project_name:
                project_name = "project"
            
            output_path = os.path.join(os.getcwd(), f"{project_name}.project")

        bundle_path_to_archive(source_path, output_path, overwrite)
        console.print(f"[green]Successfully created bundle '{output_path}' from '{source_path}'.[/green]")
    except Exception as e:
        console.print(f"[red]Error creating bundle: {e}[/red]")

import click
import os
import json
from rich.console import Console
from cli.utils.bundler import expand_bundle_to_path, bundle_path_to_archive, init_bundle_structure

console = Console()

@click.command("bundle")
@click.argument("path", required=False, default=".")
@click.option("--destination", help="Destination path for the bundle archive")
@click.option("--overwrite", is_flag=True, help="Overwrite existing bundle")
def bundle(path, destination, overwrite):
    """Bundles the project at the specified path."""
    # Proposal: bundle [path] --destination [destination_path]
    # "The *.project file will be output to the destination path."
    
    if not destination:
        # Infer destination from path or project.json
        proj_json = os.path.join(path, "project.json")
        if os.path.exists(proj_json):
            with open(proj_json, 'r') as f:
                meta = json.load(f)
                project_name = meta.get("name")
        else:
            project_name = os.path.basename(os.path.abspath(path))
        
        if not project_name:
            project_name = "project"
            
        # Default to ../project_name.project relative to the project path? 
        # Or in current cwd?
        # Proposal example: kt bundle . --destination ../svelte.project
        # If no destination, usually bundling in place or parent is weird.
        # Let's default to cwd / name.project
        destination = os.path.join(os.getcwd(), f"{project_name}.project")
        
    try:
        from cli.utils.bundler import bundle_path_to_archive
        bundle_path_to_archive(path, destination, overwrite)
        console.print(f"[green]Successfully bundled '{path}' to '{destination}'.[/green]")
    except Exception as e:
        console.print(f"[red]Error bundling project: {e}[/red]")


import click
from cli.db.session import init_db
import shutil
from pathlib import Path
import os
from cli.utils.bundler import init_bundle_structure


@click.command("init")
@click.argument("path", required=False) # For project init in path
def init_cmd(path):
    """Initializes a new project (or DB if no path)."""
    # Original init was for DB. Proposal says:
    # "Instead of an explicit init command to initialize the database, this should be done automatically... The init command will be used to initialize a new project instead."
    # "init [path] > Initializes a new project at the specified path."
    
    if path is None:
        path = "."
    
    click.echo(f"Initializing new project at {path}")
    
    target_path = Path(path)
    # target_path.mkdir(parents=True, exist_ok=True) # init_bundle_structure does this
    
    # Initialize standard project structure (project.json, templates, recipes, assets)
    try:
        init_bundle_structure(path)
        click.echo(f"Initialized scaffolding for project at {path}")
    except Exception as e:
        click.echo(f"Error initializing project structure: {e}")
        return # Stop if scaffolding fails? OR continue to try misc
    
    # Locate the misc directory relative to this file
    # init_cmd.py is in cli/commands/, so we go up 2 levels to cli, then misc
    root_dir = Path(__file__).resolve().parent.parent
    misc_dir = root_dir / "misc"
    
    if misc_dir.exists() and misc_dir.is_dir():
        # Copy misc content to target/misc
        # We want the 'misc' folder itself to be in the project structure?
        # User request: "recipe definitions in the misc folder to be included in the structure"
        # We will copy it as a 'misc' folder inside the project.
        target_misc = target_path / "misc"
        if target_misc.exists():
            click.echo(f"Warning: '{target_misc}' already exists. Skipping copy of misc definitions.")
        else:
            try:
                shutil.copytree(misc_dir, target_misc)
                click.echo(f"Included recipe definitions from misc folder into {target_misc}")
            except Exception as e:
                click.echo(f"Error copying misc folder: {e}")
    else:
            click.echo(f"Warning: Could not find misc definitions at {misc_dir}")

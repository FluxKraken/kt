import click
from cli.db.session import init_db

@click.group()
def kt():
    """Kt Template System"""
    init_db()

@kt.command()
def init():
    """Initialize the database"""
    init_db()
    click.echo("Initialized database.")

# Placeholder for importing other commands
from cli.commands.project import project
from cli.commands.template import template
from cli.commands.asset import asset
from cli.commands.recipe import recipe

kt.add_command(project)
kt.add_command(template)
kt.add_command(asset)
kt.add_command(recipe)

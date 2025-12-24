import click
from cli.db.session import init_db

@click.group()
@click.version_option()
@click.pass_context
def kt(ctx):
    """Kt Template System"""
    init_db()

# Import commands
from cli.commands.r_cmd import r_cmd
from cli.commands.project import project
from cli.commands.template import template
from cli.commands.asset import asset
from cli.commands.recipe import recipe
from cli.commands.bundle import bundle
from cli.commands.import_cmd import import_cmd
from cli.commands.init_cmd import init_cmd
from cli.commands.new_cmd import new_cmd
from cli.commands.assign_cmd import assign_cmd
from cli.commands.unassign_cmd import unassign_cmd
from cli.commands.delete_cmd import delete_cmd
from cli.commands.edit_cmd import edit_cmd
from cli.commands.list_cmd import list_cmd

# Register commands
kt.add_command(r_cmd, name="r")
kt.add_command(import_cmd, name="import")
kt.add_command(list_cmd, name="list") # Added list command
kt.add_command(init_cmd, name="init")
kt.add_command(bundle)
kt.add_command(new_cmd, name="new")
kt.add_command(edit_cmd, name="edit")
kt.add_command(recipe)
kt.add_command(template)
kt.add_command(asset)
kt.add_command(assign_cmd, name="assign")
kt.add_command(unassign_cmd, name="unassign")
kt.add_command(delete_cmd, name="delete")



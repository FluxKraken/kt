import click
from click_aliases import ClickAliasedGroup as CAG

@click.group(cls=CAG)
def kt():
    """KT Template System"""
    pass

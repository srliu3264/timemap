import typer
import sys
import os
from . import db, tui, config

app = typer.Typer()


@app.command()
def add(path: str, date: str = typer.Option(None, help="YYYY-MM-DD")):
    """Add a file path to a date."""
    abs_path = os.path.abspath(path)
    db.add_item("file", abs_path, date)
    print(f"Linked {abs_path} to {date or 'today'}")


@app.command()
def addnote(content: str, date: str = typer.Option(None, help="YYYY-MM-DD")):
    """Add a text note to a date."""
    db.add_item("note", content, date)
    print(f"Added note to {date or 'today'}")


@app.command()
def add2do(content: str):
    """Add a todo item."""
    db.add_item("todo", content)
    print("Added todo item.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context,
         config_flag: bool = typer.Option(
             False, "--config", help="Edit configuration"),
         default_flag: bool = typer.Option(False, "--default", help="Edit defaults")):

    if config_flag and default_flag:
        config.edit_config()
        return

    if ctx.invoked_subcommand is None:
        tui.run_tui()


def run():
    app()

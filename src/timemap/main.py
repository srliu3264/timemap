import typer
import sys
import os
from . import db, tui

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
    """Add a todo item (remains until checked off)."""
    db.add_item("todo", content)
    print("Added todo item.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    # If no subcommand (add/addnote/etc) is run, launch the TUI
    if ctx.invoked_subcommand is None:
        tui.run_tui()


def run():
    app()

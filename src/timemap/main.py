import typer
import sys
import os
from . import db, tui, config, output

app = typer.Typer(
    help="[bold green]TimeMap[/] - A Terminal-based Diary & Knowledge Graph Manager.",
    rich_markup_mode="rich",
    no_args_is_help=False
)
app.add_typer(output.app, name="output")


@app.command(rich_help_panel="Data Entry")
def add(path: str, date: str = typer.Option(None, help="YYYY-MM-DD")):
    """Add a file path to a date."""
    abs_path = os.path.abspath(path)
    db.add_item("file", abs_path, date)
    print(f"Linked {abs_path} to {date or 'today'}")


@app.command(rich_help_panel="Data Entry")
def addnote(content: str, date: str = typer.Option(None, help="YYYY-MM-DD")):
    """Add a text note to a date."""
    db.add_item("note", content, date)
    print(f"Added note to {date or 'today'}")


@app.command(rich_help_panel="Data Entry")
def add2do(content: str):
    """Add a todo item."""
    db.add_item("todo", content)
    print("Added todo item.")


@app.command(rich_help_panel="Data Entry")
def adddiary(title: str, content: str, mood: str = typer.Option("Neutral", help="Mood"), date: str = typer.Option(None, help="YYYY-MM-DD")):
    """Add a diary entry."""
    db.add_item("diary", content, date, alias=title, mood=mood)
    print(f"Added diary '{title}' for {date or 'today'}")


@app.command(rich_help_panel="Maintenance")
def emptytrash():
    db.empty_trash()
    print("Trash emptied.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context,
         config_flag: bool = typer.Option(
             False, "--config", help="Edit configuration"),
         default_flag: bool = typer.Option(False, "--default", help="Edit defaults")):
    """
    Welcome to [bold green]TimeMap[/]!

    [yellow]Usage:[/yellow]
    1. Run [bold]timemap[/] (no args) to launch the interactive TUI.
    2. Run [bold]timemap [command] --help[/] to see options.
    """
    if config_flag or default_flag:
        config.edit_config()
        return

    if ctx.invoked_subcommand is None:
        tui.run_tui()


def run():
    app()

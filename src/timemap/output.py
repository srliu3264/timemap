import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich import print
from datetime import datetime
from pathlib import Path

from . import db

app = typer.Typer(help="Export and Output commands")
console = Console()
APP_NAME = "timemap"

# --- CONFIG & TEMPLATE UTILS ---


def get_config_path() -> Path:
    app_dir = typer.get_app_dir(APP_NAME)
    path = Path(app_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_template_file() -> Path:
    return get_config_path() / "output_template.md"


def ensure_default_template():
    template_path = get_template_file()
    if not template_path.exists():
        default_content = (
            "+++\n"
            "title = \"{title}\"\n"
            "date = {date}\n"
            "type = \"{type}\"\n"
            "+++\n\n"
            "{content}\n"
        )
        with open(template_path, "w") as f:
            f.write(default_content)


def load_template() -> str:
    ensure_default_template()
    with open(get_template_file(), "r") as f:
        return f.read()


def parse_date_input(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%m-%d-%Y")
    except ValueError:
        print(
            f"[bold red]Error:[/] Invalid format '{date_str}'. Please use mm-dd-yyyy")
        raise typer.Exit()

# --- MAIN COMMAND ---


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    diary: bool = typer.Option(False, "--diary", help="Export only diaries"),
    note: bool = typer.Option(False, "--note", help="Export only notes"),
    config: bool = typer.Option(
        False, "--config", help="Edit the output template"),
):
    if ctx.invoked_subcommand is not None:
        return

    # 1. CONFIG MODE
    if config:
        ensure_default_template()
        template_path = get_template_file()
        print(f"[yellow]Opening template:[/] {template_path}")
        typer.edit(filename=str(template_path))
        print("[green]Template saved.[/]")
        raise typer.Exit()

    # 2. FETCH DATA
    try:
        # Returns list of tuples: (type, date_str, alias, content, mood)
        all_rows = db.get_all_entries()
    except AttributeError:
        print("[bold red]Error:[/] Could not find 'get_all_entries' in db.py.")
        raise typer.Exit()

    # 3. SET SCOPE
    export_diary = diary
    export_note = note
    # If no flags provided, default to exporting BOTH (but still filtered by type below)
    if not diary and not note:
        export_diary = True
        export_note = True

    print(f"[bold blue]TIMEMAP OUTPUT[/]")

    # 4. INTERACTIVE PROMPTS
    range_choice = Prompt.ask("Select Time Range", choices=[
                              "all", "custom"], default="all")
    start_date = None
    end_date = None

    if range_choice == "custom":
        start_date = parse_date_input(Prompt.ask("Begin date (mm-dd-yyyy)"))
        end_date = parse_date_input(Prompt.ask("End date (mm-dd-yyyy)"))

    split_folders = Confirm.ask("Split in folders (YYYY/MM/)?")
    base_path = Path("output_files")

    try:
        markdown_template = load_template()
    except Exception as e:
        print(f"[red]Template Error:[/] {e}")
        raise typer.Exit()

    count = 0

    # 5. PROCESS LOOP
    for row in all_rows:
        # Unpack the tuple from DB
        # NEW: row structure now includes MOOD at index 4
        try:
            entry_type = row[0]
            date_str = row[1]
            entry_alias = row[2]
            entry_content = row[3]
            entry_mood = row[4]
        except IndexError:
            # Fallback if DB hasn't been migrated or updated
            entry_type = row[0]
            date_str = row[1]
            entry_alias = row[2]
            entry_content = row[3]
            entry_mood = None

        # --- FILTERING ---

        # STRICTLY ignore 'todo' and 'file' types
        if entry_type not in ['diary', 'note']:
            continue

        # User flag filters
        if entry_type == "diary" and not export_diary:
            continue
        if entry_type == "note" and not export_note:
            continue

        # Date parsing and filter
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        if start_date and end_date:
            if not (start_date <= entry_date <= end_date):
                continue

        # --- DATA PREPARATION ---

        # Title Formatting
        raw_title = entry_alias if entry_alias else "Untitled"

        if entry_type == "diary":
            # Add mood to the visual title inside the file
            mood_str = entry_mood if entry_mood else ""
            if mood_str:
                display_title = f"{raw_title} ({mood_str})"
            else:
                display_title = raw_title
        else:
            display_title = "Note" if raw_title == "Untitled" else raw_title

        # Content Formatting: Markdown Line Breaks
        # Replace single newline with double newline to create paragraphs
        if entry_content:
            formatted_content = entry_content.replace("\n", "\n\n")
        else:
            formatted_content = ""

        # Filename Generation (Keep clean, no parens/moods in filename)
        if entry_type == "note":
            filename = f"{date_str}+note.md"
        else:
            # Sanitize raw title for filename
            safe_title = "".join(c for c in raw_title if c.isalnum() or c in (
                ' ', '_', '-')).strip().replace(" ", "_")
            if not safe_title:
                safe_title = "diary"
            filename = f"{date_str}+{safe_title}.md"

        # --- FILL TEMPLATE ---
        template_data = {
            "title": display_title,
            "date": date_str,
            "type": entry_type,
            "content": formatted_content
        }

        try:
            file_content = markdown_template.format(**template_data)
        except KeyError as k:
            print(f"[red]Error:[/] Template has unknown placeholder {k}")
            raise typer.Exit()

        # --- WRITE TO DISK ---
        if split_folders:
            year = entry_date.strftime("%Y")
            month = entry_date.strftime("%m")
            target_dir = base_path / year / month
        else:
            target_dir = base_path

        target_dir.mkdir(parents=True, exist_ok=True)
        final_path = target_dir / filename

        with open(final_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        count += 1
        print(f"[green]Exported:[/green] {final_path}")

    print(f"\n[bold]Done![/] {count} files exported to '{base_path}'.")

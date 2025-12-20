from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal, Container, ScrollableContainer, VerticalScroll
from textual.widgets import Header, Footer, Button, Label, ListView, ListItem, Input, TextArea, Select, Static
from textual.screen import ModalScreen
from textual.binding import Binding
from textual import on, events, work
import tempfile
import calendar
from datetime import date, timedelta, datetime
import subprocess
import os
import re
import shutil
from pathlib import Path
from textual_plotext import PlotextPlot
from . import db, config
import random

# --- UTILS ---


def open_url(url):
    try:
        subprocess.Popen(['xdg-open', url], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def get_terminal_cmd():
    terminals = ["kitty", "alacritty", "wezterm",
                 "gnome-terminal", "xfce4-terminal", "xterm"]
    env_term = os.environ.get("TERMINAL")
    if env_term and shutil.which(env_term):
        return env_term
    for term in terminals:
        if shutil.which(term):
            return term
    return "x-terminal-emulator"

# --- MODAL SCREENS ---


class CreateMenuScreen(ModalScreen):
    """Menu to choose what to create."""

    # NEW: Number keys 1-4 to select options
    BINDINGS = [
        Binding("1", "select_file", "File"),
        Binding("2", "select_note", "Note"),
        Binding("3", "select_todo", "Todo"),
        Binding("4", "select_diary", "Diary"),
        Binding("escape", "cancel", "Cancel"),
        Binding("q", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Create New Item", id="create-title"),
            Button("1. Add File", id="btn-file", variant="primary"),
            Button("2. Add Note", id="btn-note", variant="success"),
            Button("3. Add Todo", id="btn-todo", variant="warning"),
            Button("4. Add Diary", id="btn-diary", variant="error"),
            Button("Cancel", id="btn-cancel"),
            id="create-menu"
        )

    # Key Handlers
    def action_select_file(self): self.dismiss("file")
    def action_select_note(self): self.dismiss("note")
    def action_select_todo(self): self.dismiss("todo")
    def action_select_diary(self): self.dismiss("diary")
    def action_cancel(self): self.dismiss(None)

    @on(Button.Pressed)
    def on_click(self, event):
        bid = event.button.id
        if bid == "btn-file":
            self.dismiss("file")
        elif bid == "btn-note":
            self.dismiss("note")
        elif bid == "btn-todo":
            self.dismiss("todo")
        elif bid == "btn-diary":
            self.dismiss("diary")
        else:
            self.dismiss(None)


class FileAutocompleteScreen(ModalScreen):
    """Input screen with path autocomplete hints."""

    # SAFE BINDINGS: Ctrl+s to save, Esc to cancel
    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self):
        super().__init__()
        self.current_path = os.getcwd()

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Enter File Path:", classes="field-label"),
            Input(self.current_path + "/", id="file-input"),
            Label("Suggestions (Select to auto-complete):",
                  classes="field-label"),
            ListView(id="file-suggestions"),
            Horizontal(
                Button("Cancel", id="btn-cancel"),
                Button("Add", variant="primary", id="btn-add"),
                classes="dialog-buttons"
            ),
            id="file-dialog"
        )

    def on_mount(self):
        self.query_one("#file-input").focus()
        self.update_suggestions(self.query_one("#file-input").value)

    @on(Input.Changed, "#file-input")
    def on_input_change(self, event):
        self.update_suggestions(event.value)

    def update_suggestions(self, typed_value):
        list_view = self.query_one("#file-suggestions", ListView)
        list_view.clear()

        expanded_path = os.path.expanduser(typed_value)

        if os.path.isdir(expanded_path) and typed_value.endswith('/'):
            search_dir = expanded_path
            partial = ""
        else:
            search_dir = os.path.dirname(expanded_path)
            partial = os.path.basename(expanded_path)

        if not os.path.exists(search_dir):
            return

        try:
            items = sorted(os.listdir(search_dir))
            matches = [i for i in items if i.startswith(
                partial) and not i.startswith('.')]

            for m in matches:
                full = os.path.join(search_dir, m)
                display = m + ("/" if os.path.isdir(full) else "")
                list_view.append(ListItem(Label(display), name=full))
        except PermissionError:
            pass

    @on(ListView.Selected, "#file-suggestions")
    def on_suggestion_select(self, event):
        full_path = event.item.name
        input_box = self.query_one("#file-input", Input)
        if os.path.isdir(full_path) and not full_path.endswith('/'):
            full_path += "/"
        input_box.value = full_path
        input_box.focus()
        input_box.action_end()

    def action_save(self):
        path = self.query_one("#file-input").value
        self.dismiss(path)

    def action_cancel(self):
        self.dismiss(None)

    @on(Button.Pressed, "#btn-add")
    def on_add(self): self.action_save()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_btn(self): self.action_cancel()


class NoteEditScreen(ModalScreen):
    """Simple multi-line note editor."""

    # SAFE BINDINGS: Ctrl+s to save, Esc to cancel
    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, content=""):
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        yield Container(
            Label("New Note", id="note-header"),
            TextArea(self.content, id="note-content"),
            Horizontal(
                Button("Cancel", id="btn-cancel"),
                Button("Save", variant="primary", id="btn-save"),
                classes="dialog-buttons"
            ),
            id="note-dialog"
        )

    def on_mount(self): self.query_one(TextArea).focus()

    def action_save(self):
        text = self.query_one(TextArea).text
        self.dismiss(text)

    def action_cancel(self):
        self.dismiss(None)

    @on(Button.Pressed, "#btn-save")
    def on_save_btn(self): self.action_save()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_btn(self): self.action_cancel()


class DiaryEditScreen(ModalScreen):
    """Screen to edit Title, Mood, and multi-line Content."""

    # SAFE BINDINGS: Ctrl+s to save, Esc to cancel
    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    MOOD_OPTIONS = [
        ("󰱰 Happy", "󰱰"),
        ("󰱬 Sad", "󰱬"),
        ("󱃞 Neutral", "󱃞"),
        ("󰱩 Angry", "󰱩"),
        ("󱕼 Sick", "󱕼"),
        ("󰱸 Wink", "󰱸"),
        ("󰽌 Frown", "󰽌"),
        ("󰱮 Exhausted", "󰱮"),
        ("󰱫 Cool", "󰱫"),
        ("🌧Rainy", "🌧"),
        (" Cloudy", ""),
        ("❄ Snowy", "❄"),
        ("☀ Sunny", "☀"),
        ("󰱯 Mysterious", "󰱯")
    ]

    def __init__(self, title: str, mood: str, content: str):
        super().__init__()
        self.initial_title = title
        valid_moods = [m[1] for m in self.MOOD_OPTIONS]
        self.initial_mood = mood if mood in valid_moods else Select.BLANK
        self.initial_content = content

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Edit Diary Entry", id="edit-header"),
            Label("Title", classes="field-label"),
            Input(self.initial_title, id="input-title",
                  placeholder="Entry Title"),
            Label("Mood", classes="field-label"),
            Select(self.MOOD_OPTIONS, value=self.initial_mood,
                   id="input-mood", prompt="Select Mood..."),
            Label("Content", classes="field-label"),
            TextArea(self.initial_content, id="input-content"),
            Horizontal(
                Button("Cancel", id="btn-cancel"),
                Button("Save", variant="primary", id="btn-save"),
                classes="dialog-buttons"
            ),
            id="diary-edit-dialog"
        )

    def on_mount(self):
        self.query_one("#input-title").focus()

    def action_save(self):
        title = self.query_one("#input-title", Input).value
        mood = self.query_one("#input-mood").value
        if mood == Select.BLANK:
            mood = "󱃞"
        content = self.query_one("#input-content", TextArea).text
        self.dismiss({"title": title, "mood": mood, "content": content})

    def action_cancel(self):
        self.dismiss(None)

    @on(Button.Pressed, "#btn-save")
    def on_save_btn(self): self.action_save()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_btn(self): self.action_cancel()


class TextDetailScreen(ModalScreen):
    BINDINGS = [Binding("escape", "close", "Close")]

    def __init__(self, title: str, content: str, meta_info: str = ""):
        super().__init__()
        self.item_title = title
        self.item_content = content
        self.meta_info = meta_info

    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.item_title, id="detail-title"),
            Label(self.meta_info, id="detail-meta") if self.meta_info else Label(""),
            ScrollableContainer(
                Label(self.item_content, id="detail-content"),
                id="detail-scroll"
            ),
            Button("Close", variant="primary", id="btn-close"),
            id="detail-dialog"
        )

    def action_close(self): self.dismiss()
    @on(Button.Pressed, "#btn-close")
    def on_close_btn(self): self.dismiss()


class InputScreen(ModalScreen):
    # SAFE BINDINGS: Ctrl+s to save, Esc to cancel
    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, prompt: str, initial_value: str = ""):
        super().__init__()
        self.prompt_text = prompt
        self.initial_value = initial_value

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.prompt_text, id="input-label"),
            Input(self.initial_value, id="input-box"),
            Horizontal(Button("Cancel", id="btn-cancel"), Button("OK",
                       variant="primary", id="btn-ok"), classes="dialog-buttons"),
            id="input-dialog"
        )

    def on_mount(self): self.query_one(Input).focus()

    def action_save(self): self.dismiss(self.query_one(Input).value)
    def action_cancel(self): self.dismiss(None)

    @on(Button.Pressed, "#btn-ok")
    def on_ok(self): self.action_save()
    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_btn(self): self.action_cancel()
    @on(Input.Submitted)
    def on_submit(self): self.action_save()


class OpenMethodScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Open With...", id="om-label"),
            ListView(
                ListItem(Label("System Default (xdg-open)"), id="app-default"),
                ListItem(Label("Neovim (nvim)"), id="app-nvim"),
                ListItem(Label("Vim (vim)"), id="app-vim"),
                ListItem(Label("VS Code (code)"), id="app-code"),
                ListItem(Label("Custom Command..."), id="app-custom"),
                id="om-list"
            ),
            Button("Cancel", id="om-cancel"),
            id="om-dialog"
        )

    def on_mount(self): self.query_one(ListView).focus()

    @on(ListView.Selected)
    def on_select(self, event: ListView.Selected):
        cid = event.item.id
        if cid == "app-default":
            self.dismiss("xdg-open")
        elif cid == "app-nvim":
            self.dismiss("nvim")
        elif cid == "app-vim":
            self.dismiss("vim")
        elif cid == "app-code":
            self.dismiss("code")
        elif cid == "app-custom":
            self.dismiss("CUSTOM")

    @on(Button.Pressed, "#om-cancel")
    def cancel(self): self.dismiss(None)


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("?", "close_help", "Close"),
                Binding("escape", "close_help", "Close"),
                Binding("j", "scroll_down", "Scroll Down", show=False),
                Binding("k", "scroll_up", "Scroll Up", show=False)]

    def action_scroll_down(self):
        self.query_one("#help-scroll").scroll_down()

    def action_scroll_up(self):
        self.query_one("#help-scroll").scroll_up()

    def compose(self) -> ComposeResult:
        yield Container(
            Label("TimeMap Help", id="help-title"),

            VerticalScroll(
                Label("Navigation", classes="help-section-title"),
                Grid(
                    Label(
                        "h / j / k / l", classes="help-key"),     Label("Move Calendar", classes="help-desc"),
                    Label(
                        "p / t / n", classes="help-key"),     Label("Yesterday/Today/Tomorrow", classes="help-desc"),
                    Label(
                        r"\[ / ]", classes="help-key"),     Label("Last/Next Month", classes="help-desc"),
                    Label(
                        "{ / }", classes="help-key"),     Label("Last/Next Year", classes="help-desc"),
                    Label(
                        "<number>+g", classes="help-key"),  Label("Go to Day (1-31)", classes="help-desc"),
                    Label("<MM-DD-YYYY>+G", classes="help-key"),    Label(
                        "Go to Date (MM-DD-YYYY)", classes="help-desc"),
                    classes="help-grid"
                ),

                Label("Actions (Calendar)", classes="help-section-title"),
                Grid(
                    Label(
                        "v", classes="help-key"), Label("Focus/Unfocus list", classes="help-desc"),
                    Label(
                        "N (Shift+n)", classes="help-key"), Label("New Item Menu", classes="help-desc"),
                    Label(
                        "u", classes="help-key"),           Label("Recover from Trash", classes="help-desc"),
                    Label(
                        "ctrl+p", classes="help-key"),     Label("Command Palette", classes="help-desc"),
                    Label(
                        "d", classes="help-key"),           Label("Toggle Details", classes="help-desc"),
                    Label(
                        "S (shift+s)", classes="help-key"),           Label("Toggle Stats charts", classes="help-desc"),
                    Label(
                        "?", classes="help-key"),           Label("Toggle Help", classes="help-desc"),
                    Label(
                        "1-4", classes="help-key"),         Label("Select from Menu", classes="help-desc"),
                    Label(
                        "Ctrl+s", classes="help-key"),      Label("Save Item", classes="help-desc"),
                    Label(
                        "q ctrl+q", classes="help-key"),      Label("Quit TimeMap", classes="help-desc"),
                    Label("Esc", classes="help-key"),         Label("Cancel",
                                                                    classes="help-desc"),
                    classes="help-grid"
                ),
                Label("Item Types (List)", classes="help-section-title"),
                Grid(
                    Label(
                        r"\[F]ile", classes="help-key"),     Label("Path to files", classes="help-desc"),
                    Label(
                        r"\[N]ote", classes="help-key"), Label("Quick Notes (content)", classes="help-desc"),
                    Label(
                        r"\[T]odo", classes="help-key"), Label("Todo List (checkbox + content)", classes="help-desc"),
                    Label(
                        r"\[D]iary", classes="help-key"), Label("Diary (title + mood + content)", classes="help-desc"),
                    classes="help-grid"
                ),
                Label("Operations (List)", classes="help-section-title"),
                Grid(
                    Label(
                        "o", classes="help-key"),     Label(r"\[F]open / \[NTD] Details", classes="help-desc"),
                    Label(
                        "O (Shift+o)", classes="help-key"), Label(r"\[F]Open with / \[T]Follow links", classes="help-desc"),
                    Label(
                        "n", classes="help-key"), Label(r"\[F]Rename", classes="help-desc"),
                    Label(
                        "r", classes="help-key"), Label("Move to Trash", classes="help-desc"),
                    Label(
                        "R", classes="help-key"), Label("Remove (permanently)", classes="help-desc"),
                    Label(
                        "e", classes="help-key"), Label(r"\[NTD]Edit", classes="help-desc"),
                    Label(
                        "E (Shift+e)", classes="help-key"), Label(r"\[NTD]Edit with External Editor", classes="help-desc"),
                    Label(
                        "f", classes="help-key"), Label(r"\[T]Toggle Finish", classes="help-desc"),
                    classes="help-grid"
                ),
                id="help-scroll"
            ),

            Button("Close", variant="primary", id="close-help"),

            id="help-dialog"
        )

    def action_close_help(self): self.dismiss()
    def on_button_pressed(self, event): self.dismiss()


class StatsScreen(ModalScreen):
    BINDINGS = [Binding("escape", "close", "Close"),
                Binding("S", "close", "Close")]

    def __init__(self, year: int):
        super().__init__()
        self.year = year
        self.stats = db.get_year_stats(year)

    def compose(self) -> ComposeResult:
        yield Container(
            Label(f"Statistics for {self.year}", id="stats-title"),
            Grid(
                Vertical(Label("Diaries"), PlotextPlot(
                    id="plot-diary"), classes="plot-box"),
                Vertical(Label("Notes (Trend)"), PlotextPlot(
                    id="plot-note"), classes="plot-box"),
                Vertical(Label("Todos (Progress)"), PlotextPlot(
                    id="plot-todo"), classes="plot-box"),
                Vertical(Label("Files"), PlotextPlot(
                    id="plot-file"), classes="plot-box"),
                id="stats-grid"
            ),
            Button("Close", variant="primary", id="btn-stats-close"),
            id="stats-dialog"
        )

    def on_mount(self):
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        indices = list(range(len(months)))  # Use indices 0-11 for Line charts

        # 1. Diary Plot (Bar)
        p_diary = self.query_one("#plot-diary", PlotextPlot)
        p_diary.plt.bar(months, self.stats['diary'], color="magenta")
        p_diary.plt.frame(False)
        p_diary.plt.yticks(self.stats['diary'])

        # 2. Note Plot (Line Chart)
        p_note = self.query_one("#plot-note", PlotextPlot)
        p_note.plt.plot(
            indices, self.stats['note'], color="green", marker="dot")
        p_note.plt.xticks(indices, months)  # Manually label X-axis
        p_note.plt.frame(False)
        p_note.plt.ylim(0)

        # 3. Todo Plot (Stacked Bar)
        # We pass a List of Lists [[done], [pending]] to satisfy plotext structure
        t_created = sum(self.stats['todo_created'])
        t_done = sum(self.stats['todo_done'])
        t_pending = max(0, t_created - t_done)

        p_todo = self.query_one("#plot-todo", PlotextPlot)
        if t_created > 0:
            p_todo.plt.stacked_bar(
                ["Year"],                    # X-axis label
                [[t_done], [t_pending]],     # Y-axis Data Matrix
                labels=["Done", "Pending"],  # Legend Labels
                color=["cyan", "blue"]      # Colors
            )
            p_todo.plt.title(f"{int((t_done/t_created)*100)}% Complete")
            p_todo.plt.frame(False)
            p_todo.plt.ylim(0, t_created)
        else:
            p_todo.plt.title("No Data")

        # 4. File Plot (Bar)
        p_file = self.query_one("#plot-file", PlotextPlot)
        p_file.plt.bar(months, self.stats['file'], color="yellow")
        p_file.plt.frame(False)

    def action_close(self):
        self.dismiss()

    @on(Button.Pressed, "#btn-stats-close")
    def on_close_btn(self): self.dismiss()


class TagInputScreen(ModalScreen):
    # Fix Problem 4: Add Ctrl+S and Esc
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, item_id: int):
        super().__init__()
        self.item_id = item_id
        # Pre-fill with existing tags so user can edit them
        current_tags = db.get_tags_for_item(item_id)
        self.initial_value = ", ".join([t[0] for t in current_tags])

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Edit Tags (comma separated, clear to remove):",
                  classes="field-label"),
            Input(self.initial_value, id="tag-input"),
            Horizontal(
                Button("Cancel", id="btn-cancel"),
                Button("Save", variant="primary", id="btn-save"),
                classes="dialog-buttons"
            ),
            id="input-dialog"
        )

    def on_mount(self):
        # Focus input and move cursor to end
        inp = self.query_one(Input)
        inp.focus()
        inp.action_end()

    def action_save(self):
        val = self.query_one(Input).value
        # Split by comma, strip spaces, remove empty strings
        if not val or val.strip() == "":
            tags = []
        else:
            tags = [t.strip() for t in val.split(',') if t.strip()]

        # Fix Problem 1: Update (Overwrite) tags
        db.update_item_tags(self.item_id, tags)
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    @on(Button.Pressed, "#btn-save")
    def on_save(self): self.action_save()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self): self.action_cancel()

    @on(Input.Submitted)
    def on_submit(self): self.action_save()


class TagListScreen(ModalScreen):
    """Browses all tags."""
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("g", "show_graph", "Graph View"),
        Binding("v", "view_items", "View Items"),
        Binding("j", "down", "Down"),
        Binding("k", "up", "Up"),
    ]

    def compose(self) -> ComposeResult:
        tags = db.get_all_tags()
        items = []
        for t_id, t_name, count in tags:
            items.append(
                ListItem(Label(f"[{'cyan'}]{t_name}[/] ({count})"), name=str(t_id)))

        yield Container(
            Label("All Tags (Press 'v' to filter, 'g' for Graph)", id="tag-title"),
            ListView(*items, id="tag-list"),
            Button("Close", id="btn-close"),
            id="tag-dialog"
        )

    def on_mount(self): self.query_one(ListView).focus()

    def action_down(self):
        self.query_one(ListView).action_cursor_down()

    def action_up(self):
        self.query_one(ListView).action_cursor_up()

    def action_view_items(self):
        list_view = self.query_one(ListView)
        if list_view.highlighted_child:
            tag_id = int(list_view.highlighted_child.name)

            # Callback to handle the result from the filter screen
            def callback(result_date):
                if result_date:
                    # If we got a date string back, dismiss THIS screen too
                    # and pass the date up to TimeMapApp
                    self.dismiss(result_date)

            self.app.push_screen(TagFilterResultScreen(tag_id), callback)

    def action_show_graph(self):
        self.app.push_screen(TagGraphScreen())

    def action_close(self): self.dismiss(None)

    @on(Button.Pressed, "#btn-close")
    def on_close_btn(self): self.dismiss(None)


class TagFilterResultScreen(ModalScreen):
    """Shows items for a specific tag."""
    BINDINGS = [
        Binding("escape", "close", "Back"),
        Binding("v", "close", "Back"),
        Binding("q", "close", "Back"),
        Binding("d", "goto_date", "Go to Date"),  # New binding
        Binding("j", "down", "Down"),
        Binding("k", "up", "Up"),
    ]

    def __init__(self, tag_id):
        super().__init__()
        self.tag_id = tag_id

    def compose(self) -> ComposeResult:
        items = db.get_items_by_tag(self.tag_id)
        widgets = []

        if not items:
            widgets.append(ListItem(Label("No items found for this tag.")))
        else:
            for i in items:
                _, type_, content, is_done, _, alias, _, date_str = i

                display_text = ""
                icon = "●"

                if type_ == 'diary':
                    icon = ""
                    display_text = alias if alias else "Diary Entry"

                elif type_ == 'note':
                    icon = "󰏪"
                    lines = content.strip().splitlines()
                    first = lines[0] if lines else "Empty Note"
                    display_text = (
                        first[:50] + "...") if len(first) > 50 else first

                elif type_ == 'todo':
                    icon = "" if is_done else "󰆢"
                    lines = content.strip().splitlines()
                    first = lines[0] if lines else "Empty Todo"
                    display_text = (
                        first[:50] + "...") if len(first) > 50 else first

                elif type_ == 'file':
                    icon = ""
                    display_text = alias if alias else os.path.basename(
                        content)

                label_str = f"[{'cyan'}]{date_str}[/] {icon} {display_text}"

                widgets.append(ListItem(Label(label_str), name=date_str))

        yield Container(
            Label("Tagged Items (Press 'd' to jump to date)", id="tag-title"),
            ListView(*widgets, id="tag-filter-list"),
            Button("Back", id="btn-back"),
            id="tag-dialog"
        )

    def on_mount(self):
        self.query_one("#tag-filter-list").focus()

    def action_down(self):
        self.query_one("#tag-filter-list").action_cursor_down()

    def action_up(self):
        self.query_one("#tag-filter-list").action_cursor_up()

    def action_close(self):
        self.dismiss(None)

    def action_goto_date(self):
        # Retrieve the date stored in the highlighted item
        list_view = self.query_one("#tag-filter-list", ListView)
        if list_view.highlighted_child:
            date_str = list_view.highlighted_child.name
            if date_str:
                self.dismiss(date_str)  # Return the date to the parent screen

    @on(Button.Pressed, "#btn-back")
    def on_back(self): self.dismiss(None)


class TagGraphScreen(ModalScreen):
    """
    ASCII Graph Visualization:
    Star -> [Tag] -> [Item] -> [Item]
    """
    BINDINGS = [Binding("escape", "close", "Close")]

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Tag Knowledge Graph", id="graph-title"),
            ScrollableContainer(Label(self.generate_graph()), id="graph-area"),
            Button("Close", id="btn-close"),
            id="graph-dialog"
        )

    def generate_graph(self):
        tags = db.get_all_tags()
        lines = []

        # Root Star
        lines.append("[bold yellow]★ ROOT[/]")

        for t_id, t_name, _ in tags:
            # Tag Node
            lines.append(f"  └── [bold cyan]■ {t_name}[/]")

            # Get items for this tag sorted by date
            items = db.get_items_by_tag(t_id)

            # Draw chain of items
            for idx, item in enumerate(items):
                is_last = (idx == len(items) - 1)
                prefix = "      "
                connector = "└──" if is_last else "├──"

                # Color based on type
                itype = item[1]
                color = "white"
                if itype == 'diary':
                    color = "magenta"
                elif itype == 'note':
                    color = "green"
                elif itype == 'todo':
                    color = "blue"
                elif itype == 'file':
                    color = "yellow"

                name = item[5] if item[5] else item[2][:20]  # Alias or Content
                date_str = item[7]

                node = f"{prefix}{connector} [{color}]● {date_str}: {name}[/]"
                lines.append(node)

                # If we want to strictly follow "connected to adjacent items" visually:
                # The tree structure naturally implies sequence.

        return "\n".join(lines)

    @on(Button.Pressed, "#btn-close")
    def on_close(self): self.dismiss()


class DetailItem(ListItem):
    def __init__(self, item_id, type, content, is_done=False, finish_date=None, alias=None, mood=None, date_str=None):
        self.item_id = item_id
        self.type = type
        self.content = content
        self.is_done = is_done
        self.finish_date = finish_date
        self.alias = alias
        self.mood = mood
        self.date_str = date_str

        icon = ""
        display_text = alias if alias else content
        should_strike = False

        if type == 'file':
            icon = ""
            if not alias:
                display_text = os.path.basename(content)
        elif type == 'note':
            icon = "󰏪"
            display_text = content
        elif type == 'diary':
            icon = ""
            if not alias:
                display_text = f"{date_str} Diary"
        elif type == 'todo':
            display_text = content
            if is_done:
                icon = ""
                should_strike = True
                if finish_date:
                    try:
                        dt = date.fromisoformat(finish_date)
                        display_text += f" [{dt.strftime('%m/%d/%Y')}]"
                    except ValueError:
                        pass
            else:
                icon = "󰆢"

        tags = db.get_tags_for_item(item_id)
        tag_str = ""
        if tags:
            # Format: "[tag1] [tag2] "
            for t_name, t_color in tags:
                tag_str += f"[{t_color} bold]({t_name})[/] "

        super().__init__(Label(f"{icon} {tag_str} {display_text}"))
        if should_strike:
            self.add_class("todo-done")


class HeaderItem(ListItem):
    def __init__(self, title):
        super().__init__(Label(title), classes="list-header", disabled=True)


class ActionListView(ListView):
    BINDINGS = [
        Binding("o", "open_default", "Open / Details"),
        Binding("O", "open_custom", "Open With / Links"),
        Binding("n", "rename_item", "Rename"),
        Binding("R", "remove_item", "Remove"),
        Binding("r", "soft_delete", "Trash"),
        Binding("e", "edit_item", "Edit"),
        Binding("E", "edit_external", "Edit externally"),
        Binding("f", "toggle_finish", "Toggle Finish"),
        Binding("T", "add_tags", "Add Tag"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("h", "unfocus_list", "Back to Cal", show=False),
        Binding("v", "unfocus_list", "Back to Cal", show=False),
        Binding("escape", "unfocus_list", "Back to Cal", show=False),

        Binding("q", "quit", "Quit", show=False),
        Binding("?", "show_help", "Help", show=False),
        # Binding("N", "show_create_menu", "New", show=False),
        Binding("d", "toggle_view", "Toggle", show=False),
    ]

    def action_unfocus_list(self): self.app.action_focus_calendar()

    def action_open_default(self):
        """
        'o' key:
        - Todo: Show Details (Text)
        - Note/Diary: Show Details (via smart_open)
        - File: Open File (via smart_open)
        """
        item = self.highlighted_child
        if isinstance(item, DetailItem):
            if item.type == 'todo':
                # Force Details View for Todo
                self.app.push_screen(TextDetailScreen(
                    "Todo Details", item.content))
            else:
                # Default behavior for others
                self.app.action_smart_open(item)

    def action_open_custom(self):
        """
        'O' key:
        - Todo: Follow Link (via smart_open logic)
        - File: Show 'Open With' Menu
        """
        item = self.highlighted_child
        if isinstance(item, DetailItem) and item.type == 'todo':
            # Use smart_open to trigger the link opening logic
            self.app.action_smart_open(item)
        else:
            # Show "Open With" menu for files
            self.app.action_open_custom()

    def action_rename_item(self):
        item = self.highlighted_child
        if isinstance(item, DetailItem) and item.type == 'file':
            self.app.action_rename_alias(item)

    def action_remove_item(self):
        item = self.highlighted_child
        if isinstance(item, DetailItem):
            self.app.action_remove_item(item)

    def action_soft_delete(self):
        item = self.highlighted_child
        if isinstance(item, DetailItem):
            self.app.action_soft_delete_item(item)

    def action_edit_item(self):
        item = self.highlighted_child
        if isinstance(item, DetailItem) and item.type in ['note', 'todo', 'diary']:
            self.app.action_edit_item(item)

    def action_edit_external(self):
        item = self.highlighted_child
        if isinstance(item, DetailItem) and item.type in ['note', 'todo', 'diary']:
            self.app.action_edit_external(item)

    def action_toggle_finish(self):
        item = self.highlighted_child
        if isinstance(item, DetailItem) and item.type == 'todo':
            self.app.action_toggle_finish(item)

    def action_add_tags(self):
        item = self.highlighted_child
        if isinstance(item, DetailItem):
            def callback(refresh):
                if refresh:
                    self.app.refresh_ui()
            self.app.push_screen(TagInputScreen(item.item_id), callback)


class CalendarDay(Vertical):
    """
    Handles both 'Detailed' (4-corner) and 'Simple' (Color) views.
    """
    can_focus = True  # Necessary to allow keyboard navigation like a Button

    def __init__(self, day_num: int, current_year: int, current_month: int, stats: dict, simple_mode: bool):
        self.day_num = day_num
        self.stats = stats
        self.simple_mode = simple_mode
        try:
            self.full_date = date(current_year, current_month, day_num)
        except ValueError:
            self.full_date = None

        id_str = f"day-{day_num}" if day_num > 0 else None
        super().__init__(id=id_str)

        if day_num == 0:
            self.disabled = True
            self.add_class("empty-day")

        count_sum = (
            stats.get('diary', 0) +
            stats.get('file', 0) +
            stats.get('todo', 0) +
            stats.get('note', 0)
        )
        self.has_items = count_sum > 0

        if self.simple_mode and self.has_items and day_num > 0:
            self.add_class("simple-has-items")

    def compose(self) -> ComposeResult:
        if self.day_num == 0:
            return

        if self.simple_mode:
            yield Container(
                Label(str(self.day_num), classes="day-num-simple"),
                classes="day-center-simple"
            )
            return

        has_diary = self.stats.get('diary', 0) > 0
        if has_diary:
            # Use the specific mood if set, otherwise default to Nerd Font Book
            diary_icon = self.stats.get('diary_mood') or ""
        else:
            diary_icon = " "

        todo_count = self.stats.get('todo', 0)
        todo_str = f"{todo_count}" if todo_count > 0 else " "

        yield Horizontal(
            Label(diary_icon, classes="corner-icon left red"),
            Label(todo_str, classes="corner-icon right blue"),
            classes="day-row top"
        )

        # Center: Day Number
        yield Container(Label(str(self.day_num), classes="day-num"), classes="day-center")

        # Bottom Left: File+Count | Bottom Right: Note Icon+Count
        file_count = self.stats.get('file', 0)
        file_str = f"{file_count}" if file_count > 0 else " "

        note_count = self.stats.get('note', 0)
        note_str = f"󰏪{note_count}" if note_count > 0 else " "

        yield Horizontal(
            Label(file_str, classes="corner-icon left yellow"),
            Label(note_str, classes="corner-icon right green"),
            classes="day-row bottom"
        )

    def on_click(self):
        if self.full_date:
            self.app.call_from_child(self.full_date)


class TimeMapApp(App):
    CSS = """
    Screen { align: center middle; }
    #main-container { width: 100%; height: 1fr; layout: vertical; }
    #content-area { width: 100%; height: 1fr; layout: horizontal; }
    #calendar-area { width: 60%; height: 100%; }
    #details-panel { width: 40%; height: 100%; border-left: solid $accent; padding: 1; }
    #status-bar { width: 100%; height: 1; background: $accent; color: $text; padding-left: 1; text-style: bold; }
    #cal-header { height: 3; width: 100%; align: center middle; margin-bottom: 1; }
    .month-label { width: 20; text-align: center; text-style: bold; padding-top: 1; }
    .nav-btn { width: 4; } .nav-btn-year { width: 6; }
    #calendar-grid { layout: grid; grid-size: 7 7; width: 100%; height: 100%; margin: 1; }
    .day-header { width: 100%; height: 100%; text-align: center; text-style: bold; color: $accent; padding-top: 1; }
    CalendarDay { width: 100%; height: 100%; border: none; background: $surface; padding: 0 1; box-sizing: border-box; align: center middle;}
    CalendarDay:hover {background: $surface-lighten-2; }
    CalendarDay:focus { background: $accent; color: $text; }
    .selected-day { background: $primary; color: $text; text-style: bold; }

    .day-row { height: auto; width: 100%; layout: horizontal; padding: 0 1;}
    .day-center { height: auto; width: 100%; align: center middle; padding: 0; margin: 0}
    .day-num { text-style: bold; }
    .corner-icon { width: 1fr; }
    .left { text_align: left; } .right { text_align: right; }
    .red { color: #f8c8dc; } .blue { color: #8be9fd; } 
    .yellow { color: #f1fa8c; } .green { color: #50fa7b; }

    .day-center-simple { width: 100%; height: 100%; align: center middle; }
    .day-num-simple { text-style: bold; }
    .simple-has-items { background: $accent-darken-2; color: $text-accent; text-style: bold; }
    .selected-day.simple-has-items { background: $primary; color: $text; }    

    /* Dialogs */
    #input-dialog, #om-dialog, #help-dialog, #create-menu { 
        width: 60; height: auto; border: thick $background 80%; background: $surface; padding: 1; 
    }
    #file-dialog {
        width: 80%; height: 70%; border: thick $background 80%; background: $surface; padding: 1;
    }
    #create-menu { grid-size: 1; grid-gutter: 1; }
    #create-title { text-style: bold; content-align: center middle; width: 100%; border-bottom: solid $primary; margin-bottom: 1; }
    
    /* Note, Diary, File Logic */
    #diary-edit-dialog, #detail-dialog, #note-dialog {
        width: 70%; height: 80%; border: thick $background 80%; background: $surface; padding: 1 2;
    }
    #edit-header, #note-header { text-style: bold; border-bottom: solid $primary; width: 100%; content-align: center middle; margin-bottom: 1; }
    .field-label { margin-top: 1; color: $accent; text-style: bold; }
    #input-content, #note-content { height: 1fr; border: solid $secondary; margin-top: 1; }
    #file-suggestions { height: 1fr; border: solid $secondary; margin-top: 1; background: $surface-lighten-1; }

    #detail-scroll { height: 1fr; border: solid $secondary; padding: 1; margin: 1 0; background: $surface-lighten-1; }
    #detail-content { width: 100%; height: auto; }
    #detail-title { text-style: bold; content-align: center middle; width: 100%; border-bottom: solid $primary; padding-bottom: 1; }
    #detail-meta { color: $secondary; content-align: center middle; width: 100%; margin-top: 1; margin-bottom: 1; }
    
/* --- HELP SCREEN STYLES --- */
    
    #help-dialog { 
        width: 60; 
        height: 80%; 
        background: $surface;
        border: thick $background 80%; 
        layout: vertical;
    }

    #help-title { 
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        border-bottom: solid $primary;
    }

    #help-scroll {
        width: 100%;
        height: 1fr;      /* Fills space between title and button */
        padding: 0 2;
        /* VerticalScroll handles overflow-y automatically */
    }

    /* Section Headers */
    .help-section-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
        background: $surface-lighten-1;
    }

    /* Key-Value Grids */
    .help-grid {
        width: 100%;
        height: auto;
        grid-size: 2; 
        grid-gutter: 1 1; 
        margin-bottom: 1;
    }

    #close-help { 
        width: 100%;
        margin-top: 1;
    }

    .help-key { text-align: right; color: $secondary; text-style: bold; }
    .help-desc { text-align: left; }


   .list-header { background: $surface-lighten-1; color: $accent; text-style: bold; height: 1; content-align: center middle; margin: 1 0; }
    .todo-done { color: $text-muted; text-style: strike; }

    #stats-dialog {
        width: 95%;
        height: 95%;
        background: $surface;
        border: thick $background 80%;
        layout: vertical;
        padding: 1;
    }
    #stats-grid {
        width: 100%;
        height: 1fr;
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
    }
    .plot-box {
        width: 100%;
        height: 100%;
        background: $surface-lighten-1;
        padding: 1;
    }
    PlotextPlot {
        width: 100%;
        height: 1fr;
    }

    #tag-dialog, #graph-dialog {
        width: 80%; height: 80%;
        background: $surface;
        border: thick $background 80%;
        padding: 1;
    }
    #tag-title, #graph-title {
        width: 100%; text-align: center; text-style: bold; 
        border-bottom: solid $primary; margin-bottom: 1;
    }
    #graph-area { height: 1fr; border: solid $secondary; padding: 1; overflow: auto; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("?", "show_help", "Help"),
        # Nav
        Binding("h", "move_left", "Left", show=False), Binding(
            "l", "move_right", "Right", show=False),
        Binding("k", "move_up", "Up", show=False), Binding(
            "j", "move_down", "Down", show=False),
        Binding("t", "jump_today", "Today", show=False),
        Binding("p", "jump_prev", "Prev", show=False), Binding(
            "n", "jump_next", "Next", show=False),
        Binding("[", "prev_month", "-Month", show=False), Binding("]",
                                                                  "next_month", "+Month", show=False),
        Binding("{", "prev_year", "-Year", show=False), Binding("}",
                                                                "next_year", "+Year", show=False),
        Binding("G", "go_date", "Go Date", show=False),
        Binding("g", "go_day", "Go Day", show=False),
        # Actions
        Binding("v", "focus_list", "Focus List"),
        Binding("enter", "focus_list", "Focus List"),
        Binding("N", "show_create_menu", "New Item"),
        Binding("d", "toggle_view", "Toggle View"),
        Binding("u", "recover_item", "Recover"),
        Binding("S", "show_stats", "Stats"),
        Binding("C", "show_tags", "Tags"),

    ]

    def __init__(self):
        super().__init__()
        self.current_date_obj = date.today()
        self.display_year = self.current_date_obj.year
        self.display_month = self.current_date_obj.month
        self.cmd_buffer = ""
        self.simple_view = False

    def call_from_child(self, clicked_date):
        self.run_worker(self.change_selected_date(clicked_date))

    def action_toggle_view(self):
        self.simple_view = not self.simple_view
        mode_str = "Simple Mode" if self.simple_view else "Detailed Mode"
        self.notify(f"Switched to {mode_str}")
        self.run_worker(self.refresh_calendar())

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(
                Vertical(
                    Horizontal(
                        Button("<<", id="btn-prev-year",
                               classes="nav-btn-year"),
                        Button("<", id="btn-prev-month", classes="nav-btn"),
                        Label("", id="month-label", classes="month-label"),
                        Button(">", id="btn-next-month", classes="nav-btn"),
                        Button(">>", id="btn-next-year",
                               classes="nav-btn-year"),
                        id="cal-header"
                    ),
                    Container(Grid(id="calendar-grid"), id="grid-container"),
                    id="calendar-area"
                ),
                Vertical(Label("Select a date..."), id="details-panel"),
                id="content-area"
            ),
            Label("Ready.", id="status-bar"),
            id="main-container"
        )
        yield Footer()

    async def on_mount(self):
        await self.refresh_calendar()
        self.show_details()

    def on_key(self, event: events.Key):
        if event.character and event.character in "0123456789-":
            self.cmd_buffer += event.character
            self.update_status(f"Cmd: {self.cmd_buffer}")
        elif event.key == "escape":
            self.cmd_buffer = ""
            self.update_status("Ready.")
            self.action_focus_calendar()
        elif event.key == "backspace":
            self.cmd_buffer = self.cmd_buffer[:-1]
            if self.cmd_buffer:
                self.update_status(f"Cmd: {self.cmd_buffer}")
            else:
                self.update_status("Ready.")

    def update_status(self, msg):
        self.query_one("#status-bar", Label).update(msg)

    # --- ACTION HANDLERS ---

    def action_show_create_menu(self):
        """Show the new item creation menu."""
        def handler(choice):
            if not choice:
                return

            target_date_str = self.current_date_obj.isoformat()

            if choice == "file":
                self.push_screen(FileAutocompleteScreen(),
                                 lambda path: self.create_file_item(path, target_date_str))

            elif choice == "note":
                self.push_screen(NoteEditScreen(),
                                 lambda content: self.create_note_item(content, target_date_str))

            elif choice == "todo":
                self.push_screen(InputScreen("New Todo:"),
                                 lambda content: self.create_todo_item(content))

            elif choice == "diary":
                self.push_screen(DiaryEditScreen("", "", ""),
                                 lambda res: self.create_diary_item(res, target_date_str))

        self.push_screen(CreateMenuScreen(), handler)

    def create_file_item(self, path, date_str):
        if path and os.path.exists(os.path.expanduser(path)):
            db.add_item("file", os.path.abspath(
                os.path.expanduser(path)), date_str)
            self.notify(f"Linked file to {date_str}")
            self.refresh_ui()
        elif path:
            self.notify("File not found!", severity="error")

    def create_note_item(self, content, date_str):
        if content:
            db.add_item("note", content, date_str)
            self.notify("Note added")
            self.refresh_ui()

    def create_todo_item(self, content):
        if content:
            db.add_item("todo", content, self.current_date_obj.isoformat())
            self.notify("Todo added")
            self.refresh_ui()

    def create_diary_item(self, result, date_str):
        if result and result.get('content'):
            db.add_item("diary", result['content'], date_str,
                        alias=result['title'], mood=result['mood'])
            self.notify("Diary entry created")
            self.refresh_ui()

    def refresh_ui(self):
        self.show_details()
        self.run_worker(self.refresh_calendar())

    async def action_go_day(self):
        if self.cmd_buffer.isdigit():
            day = int(self.cmd_buffer)
            try:
                new_date = date(self.display_year, self.display_month, day)
                self.cmd_buffer = ""
                self.update_status(f"Jumped to day {day}")
                await self.change_selected_date(new_date)
            except ValueError:
                self.update_status("Invalid day")
                self.cmd_buffer = ""
        else:
            self.cmd_buffer = ""
            self.update_status("Ready.")

    async def action_go_date(self):
        if re.match(r"\d{1,2}-\d{1,2}-\d{4}", self.cmd_buffer):
            try:
                parts = self.cmd_buffer.split('-')
                new_date = date(int(parts[2]), int(parts[0]), int(parts[1]))
                self.cmd_buffer = ""
                self.update_status(f"Jumped to {new_date}")
                await self.change_selected_date(new_date)
            except ValueError:
                self.update_status("Invalid Date")
                self.cmd_buffer = ""
        else:
            self.update_status("Format: MM-DD-YYYY")
            self.cmd_buffer = ""

    def action_focus_list(self):
        try:
            list_view = self.query_one("ActionListView", ActionListView)
            list_view.focus()
            self.update_status("List Focused (j/k to move)")
        except Exception:
            self.notify("List is empty or not available")

    def action_focus_calendar(self):
        grid = self.query_one("#calendar-grid", Grid)
        for child in grid.children:
            if "selected-day" in child.classes:
                child.focus()
                self.update_status("Calendar Focused")
                break

    def action_remove_item(self, item):
        db.delete_item(item.item_id)
        self.refresh_ui()
        self.notify("Item removed")

    def action_soft_delete_item(self, item):
        db.soft_delete_item(item.item_id)
        self.refresh_ui()
        self.notify("Item moved to Trash (only stores 3 most recent files)")

    def action_recover_item(self):
        success = db.recover_last_deleted()
        if success:
            self.refresh_ui()
            self.notify("Last item recovered")
        else:
            self.notify("Trash is empty", severity="warning")

    def action_edit_item(self, item):
        if item.type == 'diary':
            def callback(result):
                if result:
                    db.update_diary_item(
                        item.item_id, result['title'], result['mood'], result['content'])
                    self.show_details()
                    self.notify("Diary updated")
            current_title = item.alias if item.alias else "Diary"
            self.push_screen(DiaryEditScreen(
                current_title, item.mood, item.content), callback)
        else:
            def callback(new_val):
                if new_val and new_val != item.content:
                    db.update_item_content(item.item_id, new_val)
                    self.show_details()
                    self.notify("Updated")
            self.push_screen(InputScreen(
                f"Edit {item.type}:", item.content), callback)

    def action_edit_external(self, item):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode='w+') as tf:
            tf.write(item.content or "")
            tf_path = tf.name
        with self.suspend():
            editor = config.get_editor()
            try:
                subprocess.call([editor, tf_path])
            except FileNotFoundError:
                print(f"Error: Editor '{editor}' not found")
                input("Press Enter to continue...")
        with open(tf_path, 'r') as f:
            new_content = f.read().strip()
        os.unlink(tf_path)
        if new_content != item.content:
            if item.type == 'diary':
                current_title = item.alias or ""
                current_mood = item.mood or ""
                db.update_diary_item(
                    item.item_id, current_title, current_mood, new_content)
            else:
                db.update_item_content(item.item_id, new_content)
            self.show_details()
            self.notify(f"Updated {item.type} externally")

    def action_rename_alias(self, item):
        current_val = item.alias if item.alias else os.path.basename(
            item.content)

        def callback(new_val):
            if new_val:
                db.update_item_alias(item.item_id, new_val)
                self.show_details()
                self.notify("Alias updated")
        self.push_screen(InputScreen("Rename (Alias):", current_val), callback)

    def action_toggle_finish(self, item):
        date_str = self.current_date_obj.isoformat()
        db.toggle_todo_status(item.item_id, date_str)
        status = "Done" if not item.is_done else "Undone"
        self.notify(f"Todo {status}")
        self.refresh_ui()

    def action_smart_open(self, item):
        if item.type == 'file':
            cmd = config.get_open_command(item.content)
            self.open_file(item.content, cmd)
        elif item.type == 'todo':
            match = re.search(r'\[.*?\]\((.*?)\)', item.content)
            if match:
                link = match.group(1)
                open_url(link)
                self.notify(f"Opening link: {link}")
            else:
                self.notify("No link found in todo")
        elif item.type == 'note':
            self.push_screen(TextDetailScreen("Note", item.content))
        elif item.type == 'diary':
            if item.date_str:
                try:
                    d = date.fromisoformat(item.date_str)
                    weekday = d.strftime("%A")
                    meta = f"{item.date_str} | {
                        weekday} | Mood: {item.mood or 'N/A'}"
                except ValueError:
                    meta = ""
            else:
                meta = ""
            title = item.alias if item.alias else "Diary"
            self.push_screen(TextDetailScreen(title, item.content, meta))

    def action_open_custom(self):
        try:
            list_view = self.query_one("ActionListView", ActionListView)
            if list_view.has_focus and isinstance(list_view.highlighted_child, DetailItem):
                item = list_view.highlighted_child
                if item and item.type == 'file':
                    def callback(method):
                        if method == "CUSTOM":
                            self.push_screen(InputScreen("Enter command:"), lambda cmd: self.open_file(
                                item.content, cmd) if cmd else None)
                        elif method:
                            self.open_file(item.content, method)
                    self.push_screen(OpenMethodScreen(), callback)
        except Exception:
            pass

    def action_show_stats(self):
        self.push_screen(StatsScreen(self.display_year))

    def action_show_tags(self):
        def callback(result):
            if result:
                # 'result' is the date string returned from the tag screens
                try:
                    target_date = date.fromisoformat(result)
                    # Use existing helper to update calendar and focus
                    self.call_from_child(target_date)
                    self.notify(f"Jumped to {target_date}")
                except ValueError:
                    pass

        self.app.push_screen(TagListScreen(), callback)

    def open_file(self, path, command):
        if not os.path.exists(path):
            self.notify("File missing", severity="error")
            return
        cmd_list = [command, path]
        term_apps = ['nvim', 'vim', 'vi', 'nano', 'htop', 'less', 'top']
        if os.path.basename(command) in term_apps:
            term = get_terminal_cmd()
            cmd_list = [term, "-e", command, path]
        try:
            subprocess.Popen(cmd_list, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            self.notify(f"Command '{command}' not found", severity="error")

    def action_show_help(self): self.push_screen(HelpScreen())

    async def refresh_calendar(self):
        month_name = calendar.month_name[self.display_month]
        self.query_one(
            "#month-label", Label).update(f"{month_name} {self.display_year}")
        grid = self.query_one("#calendar-grid", Grid)
        await grid.remove_children()
        for d in calendar.day_abbr:
            grid.mount(Label(d, classes="day-header"))

        cal = calendar.monthcalendar(self.display_year, self.display_month)
        stats = db.get_month_stats(self.display_year, self.display_month)

        day_to_focus = None
        for week in cal:
            for day in week:
                day_stats = stats.get(day, {})
                widget = CalendarDay(
                    day, self.display_year, self.display_month, day_stats, self.simple_view)

                if day != 0:
                    if date(self.display_year, self.display_month, day) == self.current_date_obj:
                        widget.add_class("selected-day")
                        day_to_focus = widget
                grid.mount(widget)

        try:
            if not self.query_one("ActionListView").has_focus and day_to_focus:
                day_to_focus.focus()
        except Exception:
            if day_to_focus:
                day_to_focus.focus()

    def show_details(self):
        target_date_str = self.current_date_obj.isoformat()
        panel = self.query_one("#details-panel")
        panel.remove_children()
        panel.mount(Label(f"Items for {target_date_str}:"))
        try:
            items = db.get_items_for_date(target_date_str)
        except Exception:
            items = []

        date_items = [i for i in items if i[1] != 'todo' and i[1] != 'diary']
        todo_items = [i for i in items if i[1] == 'todo']
        diary_items = [i for i in items if i[1] == 'diary']

        todo_items.sort(key=lambda x: x[3])

        widgets = []
        for i in date_items:
            widgets.append(DetailItem(
                i[0], i[1], i[2], i[3], i[4], i[5], i[6], target_date_str))
        if todo_items:
            widgets.append(HeaderItem("── To Do List ──"))
            for i in todo_items:
                widgets.append(DetailItem(
                    i[0], i[1], i[2], i[3], i[4], i[5], i[6], target_date_str))
        if diary_items:
            widgets.append(HeaderItem("── Diaries ──"))
            for i in diary_items:
                widgets.append(DetailItem(
                    i[0], i[1], i[2], i[3], i[4], i[5], i[6], target_date_str))

        if not widgets:
            panel.mount(Label("No items found."))
        else:
            list_view = ActionListView(*widgets)
            panel.mount(list_view)

    async def change_selected_date(self, new_date: date):
        self.current_date_obj = new_date
        if (new_date.year != self.display_year) or (new_date.month != self.display_month):
            self.display_year, self.display_month = new_date.year, new_date.month
            await self.refresh_calendar()
        else:
            await self.refresh_calendar()
        self.show_details()

    async def action_move_left(self): await self.change_selected_date(
        self.current_date_obj - timedelta(days=1))

    async def action_move_right(self): await self.change_selected_date(
        self.current_date_obj + timedelta(days=1))

    async def action_move_up(self): await self.change_selected_date(
        self.current_date_obj - timedelta(weeks=1))

    async def action_move_down(self): await self.change_selected_date(
        self.current_date_obj + timedelta(weeks=1))

    async def action_jump_today(
        self): await self.change_selected_date(date.today())

    async def action_jump_prev(self):
        await self.change_selected_date(date.today() - timedelta(days=1))

    async def action_jump_next(self):
        await self.change_selected_date(date.today() + timedelta(days=1))

    async def action_prev_month(self):
        if self.display_month == 1:
            self.display_month = 12
            self.display_year -= 1
        else:
            self.display_month -= 1
        await self.refresh_calendar()

    async def action_next_month(self):
        if self.display_month == 12:
            self.display_month = 1
            self.display_year += 1
        else:
            self.display_month += 1
        await self.refresh_calendar()

    async def action_prev_year(self):
        self.display_year -= 1
        await self.refresh_calendar()

    async def action_next_year(self):
        self.display_year += 1
        await self.refresh_calendar()

    @on(Button.Pressed, "#btn-prev-month")
    async def on_prev_month_click(self): await self.action_prev_month()
    @on(Button.Pressed, "#btn-next-month")
    async def on_next_month_click(self): await self.action_next_month()
    @on(Button.Pressed, "#btn-prev-year")
    async def on_prev_year_click(self): await self.action_prev_year()
    @on(Button.Pressed, "#btn-next-year")
    async def on_next_year_click(self): await self.action_next_year()

    @on(Button.Pressed)
    async def on_day_click(self, event: Button.Pressed):
        if isinstance(event.button, CalendarDay) and event.button.full_date:
            await self.change_selected_date(event.button.full_date)

    @on(ListView.Selected)
    def on_item_click(self, event: ListView.Selected): pass


def run_tui():
    app = TimeMapApp()
    app.run()
    app.run()
    app.run()

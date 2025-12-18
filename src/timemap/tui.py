from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Button, Label, ListView, ListItem, Input
from textual.screen import ModalScreen
from textual.binding import Binding
from textual import on, events
import calendar
from datetime import date, timedelta, datetime
import subprocess
import os
import re
import shutil

from . import db, config

# --- UTILS ---


def open_url(url):
    try:
        subprocess.Popen(['xdg-open', url], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def get_terminal_cmd():
    """Detects the user's terminal emulator."""
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


class InputScreen(ModalScreen):
    def __init__(self, prompt: str, initial_value: str = ""):
        super().__init__()
        self.prompt_text = prompt
        self.initial_value = initial_value

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.prompt_text, id="input-label"),
            Input(self.initial_value, id="input-box"),
            Horizontal(
                Button("Cancel", id="btn-cancel"),
                Button("OK", variant="primary", id="btn-ok"),
                classes="dialog-buttons"
            ),
            id="input-dialog"
        )

    def on_mount(self):
        self.query_one(Input).focus()

    @on(Button.Pressed, "#btn-ok")
    def on_ok(self):
        val = self.query_one(Input).value
        self.dismiss(val)

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self):
        self.dismiss(None)

    @on(Input.Submitted)
    def on_submit(self):
        self.on_ok()


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

    def on_mount(self):
        self.query_one(ListView).focus()

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
    def cancel(self):
        self.dismiss(None)


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("?", "close_help", "Close"),
                Binding("escape", "close_help", "Close")]

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("TimeMap Help", id="help-title"),
            Label("Navigation", classes="help-header"),
            Label("h / l", classes="help-key"), Label("Prev / Next Day",
                                                      classes="help-desc"),
            Label("k / j", classes="help-key"), Label("Prev / Next Week",
                                                      classes="help-desc"),
            Label("t", classes="help-key"),     Label("Jump to Today",
                                                      classes="help-desc"),
            Label("Item Actions", classes="help-header"),
            Label("o", classes="help-key"),     Label("Open / Open Link",
                                                      classes="help-desc"),
            Label("e", classes="help-key"),     Label("Edit Note/Todo",
                                                      classes="help-desc"),
            Label("f", classes="help-key"),     Label("Toggle Finish (Todo)",
                                                      classes="help-desc"),
            Label("r", classes="help-key"),     Label("Remove Item",
                                                      classes="help-desc"),
            Label("ctrl+n", classes="help-key"), Label("Rename File Alias",
                                                       classes="help-desc"),
            Label("General", classes="help-header"),
            Label("?", classes="help-key"),     Label("Close Help",
                                                      classes="help-desc"),
            Label("q", classes="help-key"),     Label("Quit", classes="help-desc"),
            Button("Close", variant="primary", id="close-help"),
            id="help-dialog"
        )

    def action_close_help(self): self.dismiss()
    def on_button_pressed(self, event): self.dismiss()

# --- CUSTOM WIDGETS ---


class DetailItem(ListItem):
    def __init__(self, item_id, type, content, is_done=False, finish_date=None, alias=None):
        self.item_id = item_id
        self.type = type
        self.content = content
        self.is_done = is_done
        self.finish_date = finish_date
        self.alias = alias

        icon = ""
        display_text = alias if alias else content
        should_strike = False

        if type == 'file':
            icon = "📁"
            if not alias:
                display_text = os.path.basename(content)
        elif type == 'note':
            icon = "📝"
            display_text = content
        elif type == 'todo':
            display_text = content
            if is_done:
                icon = "✅"
                should_strike = True
                if finish_date:
                    try:
                        dt = date.fromisoformat(finish_date)
                        display_text += f" [{dt.strftime('%m/%d/%Y')}]"
                    except ValueError:
                        pass
            else:
                icon = "⬜"

        super().__init__(Label(f"{icon} {display_text}"))
        if should_strike:
            self.add_class("todo-done")


class HeaderItem(ListItem):
    def __init__(self, title):
        super().__init__(Label(title), classes="list-header", disabled=True)


class ActionListView(ListView):
    """Handles key events for the focused list."""

    def on_key(self, event: events.Key):
        if not isinstance(self.highlighted_child, DetailItem):
            return
        item = self.highlighted_child
        key = event.key

        if key == "r":
            self.app.action_remove_item(item)
        elif key == "e":
            if item.type in ['note', 'todo']:
                self.app.action_edit_item(item)
        elif key == "f":
            if item.type == 'todo':
                self.app.action_toggle_finish(item)
        elif key == "ctrl+n":
            if item.type == 'file':
                self.app.action_rename_alias(item)
        elif key == "o":
            self.app.action_smart_open(item)
        elif key == "O":  # Shift+o
            self.app.action_open_custom()


class CalendarDay(Button):
    def __init__(self, day_num: int, current_year: int, current_month: int, has_items: bool):
        self.day_num = day_num
        if day_num != 0:
            try:
                self.full_date = date(current_year, current_month, day_num)
            except ValueError:
                self.full_date = None
            label = str(day_num) + (" ★" if has_items else "")
            id_str = f"day-{day_num}"
            disabled_flag = False
        else:
            self.full_date = None
            label = ""
            id_str = None
            disabled_flag = True
        super().__init__(label, id=id_str, disabled=disabled_flag)
        if has_items:
            self.add_class("has-items")


class TimeMapApp(App):
    CSS = """
    Screen { align: center middle; }
    #calendar-area { width: 60%; height: 100%; }
    #details-panel { width: 40%; height: 100%; border-left: solid $accent; padding: 1; }
    #cal-header { height: 3; width: 100%; align: center middle; margin-bottom: 1; }
    .month-label { width: 20; text-align: center; text-style: bold; padding-top: 1; }
    .nav-btn { width: 4; } .nav-btn-year { width: 6; }
    #calendar-grid { layout: grid; grid-size: 7 7; width: 100%; height: 100%; margin: 1; }
    .day-header { width: 100%; height: 100%; text-align: center; text-style: bold; color: $accent; padding-top: 1; }
    CalendarDay { width: 100%; height: 100%; }
    .selected-day { background: $primary; color: $text; text-style: bold; }
    .has-items { color: $accent-lighten-2; }
    .todo-done { color: $text-muted; text-style: strike; }
    .list-header { background: $surface-lighten-1; color: $accent; text-style: bold; height: 1; content-align: center middle; margin: 1 0; }
    
    #input-dialog, #om-dialog, #help-dialog { width: 60; height: auto; border: thick $background 80%; background: $surface; padding: 1; }
    #help-dialog { grid-size: 2; grid-gutter: 1 2; }
    .dialog-buttons { align: center middle; margin-top: 1; height: 3; }
    #input-label { margin-bottom: 1; }
    #help-title { column-span: 2; content-align: center middle; text-style: bold; border-bottom: solid $primary; margin-bottom: 1; }
    .help-header { column-span: 2; content-align: center middle; text-style: bold; color: $accent; margin-top: 1; }
    .help-key { text-align: right; color: $secondary; text-style: bold; }
    .help-desc { text-align: left; }
    #close-help { column-span: 2; margin-top: 2; }
    """

    BINDINGS = [
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
        Binding("?", "show_help", "Help", show=True), Binding(
            "q", "quit", "Quit", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.current_date_obj = date.today()
        self.display_year = self.current_date_obj.year
        self.display_month = self.current_date_obj.month

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Horizontal(
                    Button("<<", id="btn-prev-year", classes="nav-btn-year"),
                    Button("<", id="btn-prev-month", classes="nav-btn"),
                    Label("", id="month-label", classes="month-label"),
                    Button(">", id="btn-next-month", classes="nav-btn"),
                    Button(">>", id="btn-next-year", classes="nav-btn-year"),
                    id="cal-header"
                ),
                Container(Grid(id="calendar-grid"), id="grid-container"),
                id="calendar-area"
            ),
            Vertical(Label("Select a date..."), id="details-panel")
        )
        yield Footer()

    async def on_mount(self):
        await self.refresh_calendar()
        self.show_details()

    def action_show_help(self): self.push_screen(HelpScreen())

    # --- ITEM LOGIC ---

    def action_remove_item(self, item: DetailItem):
        db.delete_item(item.item_id)
        self.show_details()
        self.run_worker(self.refresh_calendar())
        self.notify("Item removed")

    def action_edit_item(self, item: DetailItem):
        def callback(new_val):
            if new_val and new_val != item.content:
                db.update_item_content(item.item_id, new_val)
                self.show_details()
                self.notify("Updated")
        self.push_screen(InputScreen(
            f"Edit {item.type}:", item.content), callback)

    def action_rename_alias(self, item: DetailItem):
        current_val = item.alias if item.alias else os.path.basename(
            item.content)

        def callback(new_val):
            if new_val:
                db.update_item_alias(item.item_id, new_val)
                self.show_details()
                self.notify("Alias updated")
        self.push_screen(InputScreen("Rename (Alias):", current_val), callback)

    def action_toggle_finish(self, item: DetailItem):
        date_str = self.current_date_obj.isoformat()
        db.toggle_todo_status(item.item_id, date_str)
        status = "Done" if not item.is_done else "Undone"
        self.notify(f"Todo {status}")
        self.show_details()
        self.run_worker(self.refresh_calendar())

    def action_smart_open(self, item: DetailItem):
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

    def open_file(self, path, command):
        if not os.path.exists(path):
            self.notify("File missing", severity="error")
            return

        cmd_list = [command, path]
        term_apps = ['nvim', 'vim', 'vi', 'nano', 'htop', 'less', 'top']
        cmd_name = os.path.basename(command)

        if cmd_name in term_apps:
            term = get_terminal_cmd()
            cmd_list = [term, "-e", command, path]
            self.notify(f"Launching in {term}...")
        else:
            self.notify(f"Opened with {command}")

        try:
            subprocess.Popen(cmd_list, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            self.notify(f"Command '{command}' not found", severity="error")

    # --- REFRESH LOGIC ---

    async def refresh_calendar(self):
        month_name = calendar.month_name[self.display_month]
        self.query_one(
            "#month-label", Label).update(f"{month_name} {self.display_year}")
        grid = self.query_one("#calendar-grid", Grid)
        await grid.remove_children()
        for d in calendar.day_abbr:
            grid.mount(Label(d, classes="day-header"))

        cal = calendar.monthcalendar(self.display_year, self.display_month)
        marked_days = db.get_marked_days(self.display_year, self.display_month)

        day_to_focus = None
        for week in cal:
            for day in week:
                btn = CalendarDay(day, self.display_year,
                                  self.display_month, (day in marked_days))
                if day != 0:
                    if date(self.display_year, self.display_month, day) == self.current_date_obj:
                        btn.add_class("selected-day")
                        day_to_focus = btn
                grid.mount(btn)
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

        date_items = [i for i in items if i[1] != 'todo']
        todo_items = [i for i in items if i[1] == 'todo']
        todo_items.sort(key=lambda x: x[3])

        widgets = []
        for i in date_items:
            widgets.append(DetailItem(i[0], i[1], i[2], i[3], i[4], i[5]))
        if todo_items:
            widgets.append(HeaderItem("── To Do List ──"))
            for i in todo_items:
                widgets.append(DetailItem(i[0], i[1], i[2], i[3], i[4], i[5]))

        if not widgets:
            panel.mount(Label("No items found."))
        else:
            list_view = ActionListView(*widgets)
            panel.mount(list_view)

    # --- NAVIGATION ---

    async def change_selected_date(self, new_date: date):
        self.current_date_obj = new_date
        if (new_date.year != self.display_year) or (new_date.month != self.display_month):
            self.display_year, self.display_month = new_date.year, new_date.month
            await self.refresh_calendar()
        else:
            await self.refresh_calendar()
        self.show_details()

    async def action_move_left(self):
        await self.change_selected_date(self.current_date_obj - timedelta(days=1))

    async def action_move_right(self):
        await self.change_selected_date(self.current_date_obj + timedelta(days=1))

    async def action_move_up(self):
        await self.change_selected_date(self.current_date_obj - timedelta(weeks=1))

    async def action_move_down(self):
        await self.change_selected_date(self.current_date_obj + timedelta(weeks=1))

    async def action_jump_today(self):
        await self.change_selected_date(date.today())

    async def action_jump_prev(self):
        await self.change_selected_date(self.current_date_obj - timedelta(days=1))

    async def action_jump_next(self):
        await self.change_selected_date(self.current_date_obj + timedelta(days=1))

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
    async def on_prev_month_click(self):
        await self.action_prev_month()

    @on(Button.Pressed, "#btn-next-month")
    async def on_next_month_click(self):
        await self.action_next_month()

    @on(Button.Pressed, "#btn-prev-year")
    async def on_prev_year_click(self):
        await self.action_prev_year()

    @on(Button.Pressed, "#btn-next-year")
    async def on_next_year_click(self):
        await self.action_next_year()

    @on(Button.Pressed)
    async def on_day_click(self, event: Button.Pressed):
        if isinstance(event.button, CalendarDay) and event.button.full_date:
            await self.change_selected_date(event.button.full_date)

    @on(ListView.Selected)
    def on_item_click(self, event: ListView.Selected):
        pass


def run_tui():
    app = TimeMapApp()
    app.run()

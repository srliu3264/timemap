from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Button, Label, ListView, ListItem
from textual.screen import ModalScreen
from textual.binding import Binding
from textual import on
import calendar
from datetime import date, timedelta
import subprocess
import os

from . import db

# --- HELP SCREEN ---


class HelpScreen(ModalScreen):
    """Screen with a dialog to show keybindings."""
    BINDINGS = [
        Binding("?", "close_help", "Close Help"),
        Binding("escape", "close_help", "Close Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("TimeMap Help", id="help-title"),
            Label("Navigation", classes="help-header"),
            Label("h / l", classes="help-key"), Label("Previous / Next Day",
                                                      classes="help-desc"),
            Label("k / j", classes="help-key"), Label("Previous / Next Week",
                                                      classes="help-desc"),
            Label("t", classes="help-key"),     Label("Jump to Today",
                                                      classes="help-desc"),
            Label("p / n", classes="help-key"), Label("Yesterday / Tomorrow",
                                                      classes="help-desc"),
            Label("Month/Year", classes="help-header"),
            Label("[ / ]", classes="help-key"), Label("Prev / Next Month",
                                                      classes="help-desc"),
            Label("{ / }", classes="help-key"), Label("Prev / Next Year",
                                                      classes="help-desc"),
            Label("General", classes="help-header"),
            Label("?", classes="help-key"),     Label("Close this help",
                                                      classes="help-desc"),
            Label("q", classes="help-key"),     Label("Quit", classes="help-desc"),
            Button("Close", variant="primary", id="close-help"),
            id="help-dialog"
        )

    def action_close_help(self):
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

# --- WIDGETS ---


class CalendarDay(Button):
    def __init__(self, day_num: int, current_year: int, current_month: int):
        self.day_num = day_num
        if day_num != 0:
            try:
                self.full_date = date(current_year, current_month, day_num)
            except ValueError:
                self.full_date = None
            label = str(day_num)
            id_str = f"day-{day_num}"
            disabled_flag = False
        else:
            self.full_date = None
            label = ""
            id_str = None
            disabled_flag = True
        super().__init__(label, id=id_str, disabled=disabled_flag)


class DetailItem(ListItem):
    """A list item representing a file, note, or todo."""

    def __init__(self, item_id, type, content, is_done=False):
        # 1. Determine visual state first
        icon = ""
        display_text = content

        should_strike = False

        if type == 'file':
            icon = "📁"
        elif type == 'note':
            icon = "📝"
        elif type == 'todo':
            if is_done:
                icon = "✅"
                should_strike = True
            else:
                icon = "⬜"

        # 2. Call super() FIRST to initialize the widget
        super().__init__(Label(f"{icon} {display_text}"))

        # 3. NOW set attributes and classes
        self.item_id = item_id
        self.type = type
        self.content = content
        self.is_done = is_done

        if should_strike:
            self.add_class("todo-done")


class HeaderItem(ListItem):
    """A non-selectable separator header."""

    def __init__(self, title):
        super().__init__(Label(title), classes="list-header", disabled=True)


class TimeMapApp(App):
    CSS = """
    Screen { align: center middle; }
    
    /* Layout */
    #calendar-area { width: 60%; height: 100%; }
    #details-panel { width: 40%; height: 100%; border-left: solid $accent; padding: 1; }
    
    /* Calendar Header */
    #cal-header { height: 3; width: 100%; align: center middle; margin-bottom: 1; }
    .month-label { width: 20; text-align: center; text-style: bold; padding-top: 1; }
    .nav-btn { width: 4; }
    .nav-btn-year { width: 6; }

    /* Grid */
    #calendar-grid { layout: grid; grid-size: 7 7; width: 100%; height: 100%; margin: 1; }
    .day-header { width: 100%; height: 100%; text-align: center; text-style: bold; color: $accent; padding-top: 1; }
    CalendarDay { width: 100%; height: 100%; }
    .selected-day { background: $primary; color: $text; text-style: bold; }

    /* --- ITEM LIST CSS --- */
    .todo-done {
        color: $text-muted;
        text-style: strike;
    }
    
    .list-header {
        background: $surface-lighten-1;
        color: $accent;
        text-style: bold;
        height: 1;
        content-align: center middle;
        margin-top: 1;
        margin-bottom: 0;
    }

    /* --- HELP DIALOG CSS --- */
    #help-dialog { grid-size: 2; grid-gutter: 1 2; grid-rows: 1fr 3; padding: 0 1; width: 60; height: auto; border: thick $background 80%; background: $surface; }
    #help-title { column-span: 2; height: 1fr; width: 1fr; content-align: center middle; text-style: bold; border-bottom: solid $primary; margin-bottom: 1; }
    .help-header { column-span: 2; width: 1fr; content-align: center middle; text-style: bold; color: $accent; margin-top: 1; }
    .help-key { text-align: right; color: $secondary; text-style: bold; }
    .help-desc { text-align: left; }
    #close-help { column-span: 2; width: 1fr; margin-top: 2; }
    """

    BINDINGS = [
        Binding("h", "move_left", "Prev Day", show=False),
        Binding("l", "move_right", "Next Day", show=False),
        Binding("k", "move_up", "Prev Week", show=False),
        Binding("j", "move_down", "Next Week", show=False),
        Binding("t", "jump_today", "Today", show=False),
        Binding("p", "jump_prev", "Yesterday", show=False),
        Binding("n", "jump_next", "Tomorrow", show=False),
        Binding("[", "prev_month", "-Month", show=False),
        Binding("]", "next_month", "+Month", show=False),
        Binding("{", "prev_year", "-Year", show=False),
        Binding("}", "next_year", "+Year", show=False),
        Binding("?", "show_help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
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

    def action_show_help(self):
        self.push_screen(HelpScreen())

    async def refresh_calendar(self):
        month_name = calendar.month_name[self.display_month]
        label = self.query_one("#month-label", Label)
        label.update(f"{month_name} {self.display_year}")
        grid = self.query_one("#calendar-grid", Grid)
        await grid.remove_children()

        for day_name in calendar.day_abbr:
            grid.mount(Label(day_name, classes="day-header"))

        cal = calendar.monthcalendar(self.display_year, self.display_month)
        day_to_focus = None
        for week in cal:
            for day in week:
                btn = CalendarDay(day, self.display_year, self.display_month)
                if day != 0:
                    btn_date = date(self.display_year, self.display_month, day)
                    if btn_date == self.current_date_obj:
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

        # Sort Todos: Unfinished (0) first, Done (1) last
        todo_items.sort(key=lambda x: x[3])

        widgets_to_show = []

        if date_items:
            for item in date_items:
                widgets_to_show.append(DetailItem(
                    item[0], item[1], item[2], item[3]))

        if todo_items:
            widgets_to_show.append(HeaderItem("── To Do List ──"))
            for item in todo_items:
                widgets_to_show.append(DetailItem(
                    item[0], item[1], item[2], item[3]))

        if not widgets_to_show:
            panel.mount(Label("No items found."))
        else:
            list_view = ListView(*widgets_to_show)
            panel.mount(list_view)

    # --- ACTIONS & HANDLERS ---

    async def change_selected_date(self, new_date: date):
        self.current_date_obj = new_date
        if (new_date.year != self.display_year) or (new_date.month != self.display_month):
            self.display_year = new_date.year
            self.display_month = new_date.month
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
        if isinstance(event.item, DetailItem):
            item = event.item
            if item.type == 'file':
                if os.path.exists(item.content):
                    subprocess.Popen(['xdg-open', item.content], start_new_session=True,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.notify(f"Opening {item.content}")
                else:
                    self.notify("File not found!", severity="error")
            elif item.type == 'todo':
                db.toggle_todo_status(item.item_id)
                status = "Done" if not item.is_done else "Undone"
                self.notify(f"Todo marked {status}")
                self.show_details()
            elif item.type == 'note':
                self.notify(item.content, title="Note", timeout=5)


def run_tui():
    app = TimeMapApp()
    app.run()

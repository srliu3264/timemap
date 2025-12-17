from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Label, ListView, ListItem
from textual import on
import calendar
from datetime import date
import subprocess
import os

from . import db


class CalendarDay(Button):
    """A button representing a day in the calendar."""

    def __init__(self, day_num: int, current_date: date):
        self.day_num = day_num
        # Handle empty days (0)
        if day_num != 0:
            self.full_date = current_date.replace(day=day_num).isoformat()
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

    def __init__(self, item_id, type, content):
        self.item_id = item_id
        self.type = type
        self.content = content
        icon = "📁" if type == 'file' else "📝" if type == 'note' else "TODO"
        super().__init__(Label(f"{icon} {content}"))


class TimeMapApp(App):
    CSS = """
    Screen { align: center middle; }
    #calendar-grid {
        layout: grid;
        grid-size: 7 6;
        width: 100%;
        height: 100%;
        margin: 1;
    }
    #calendar-container { width: 60%; height: 100%; }
    #details-panel { width: 40%; height: 100%; border-left: solid green; padding: 1; }
    CalendarDay { width: 100%; height: 100%; }
.month-header { text-align: center; width: 100%; background: $accent; color: auto; text-style: bold;}    """

    def __init__(self):
        super().__init__()
        self.selected_date = date.today().isoformat()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(id="calendar-container"),
            Vertical(Label("Select a date..."), id="details-panel")
        )
        yield Footer()

    def on_mount(self):
        self.refresh_calendar()
        self.show_details(self.selected_date)

    def refresh_calendar(self):
        container = self.query_one("#calendar-container")
        container.remove_children()

        today = date.today()

        # 1. Add the Month Header
        container.mount(
            Label(f"{today.strftime('%B %Y')}", classes="month-header"))

        # 2. Create and Mount the Grid FIRST
        grid = Grid(id="calendar-grid")
        container.mount(grid)

        # 3. NOW we can add children to the Grid because it is attached to the DOM
        cal = calendar.monthcalendar(today.year, today.month)

        for week in cal:
            for day in week:
                grid.mount(CalendarDay(day, today))

    def show_details(self, target_date):
        panel = self.query_one("#details-panel")
        panel.remove_children()

        panel.mount(Label(f"Items for {target_date}:"))

        try:
            items = db.get_items_for_date(target_date)
        except Exception:
            # Handle case where DB might not be initialized yet in edge cases
            items = []

        if not items:
            panel.mount(Label("No items found."))
            return

        list_view = ListView()
        for item in items:
            # item structure: (id, type, content, is_done)
            list_view.append(DetailItem(item[0], item[1], item[2]))

        panel.mount(list_view)

    @on(Button.Pressed)
    def on_day_click(self, event: Button.Pressed):
        # Only react if it's a CalendarDay (not some other button)
        if isinstance(event.button, CalendarDay) and event.button.full_date:
            self.selected_date = event.button.full_date
            self.show_details(self.selected_date)

    @on(ListView.Selected)
    def on_item_click(self, event: ListView.Selected):
        item = event.item
        if item.type == 'file':
            if os.path.exists(item.content):
                # Detach process so TUI doesn't freeze
                subprocess.Popen(['xdg-open', item.content],
                                 start_new_session=True,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                self.notify(f"Opening {item.content}")
            else:
                self.notify("File not found!", severity="error")
        elif item.type == 'todo':
            db.mark_todo_done(item.item_id)
            self.notify("Todo marked as done!")
            self.show_details(self.selected_date)
        elif item.type == 'note':
            self.notify(item.content, title="Note", timeout=5)


def run_tui():
    app = TimeMapApp()
    app.run()

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import QSize, QThread, QTimer, pyqtSignal, pyqtSlot

from ami.gui.widgets import HeadspaceWidget

from .cal_config import CalendarConfig
from .google_sync import GoogleAuth
from .json_calendar import JsonCalendar
from .common import DateRange, Event

class EventWidget(QFrame):
    def __init__(self, event: Event, font_family: str, font_size: int):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Set background color
        self.setStyleSheet(f"background-color: {event.color}; border: 1px solid black;")

        if event.time is None:
            name_label = QLabel(event.name)
            name_label.setWordWrap(True)
            name_label.setStyleSheet(f"""
                font-family: {font_family};
                font-size: {font_size}px;
                color: black;
                background-color: transparent;
            """)
            layout.addWidget(name_label)
        else:
            name_label = QLabel(event.name)
            name_label.setWordWrap(True)
            name_label.setStyleSheet(f"""
                font-family: {font_family};
                font-size: {font_size}px;
                font-weight: bold;
                color: black;
                background-color: transparent;
            """)

            time = event.time.strftime("%I:%M %p").lstrip("0").lower()
            time_label = QLabel(time)
            time_label.setStyleSheet(f"""
                font-family: {font_family};
                font-size: {font_size}px;
                color: black;
                background-color: transparent;
            """)

            layout.addWidget(name_label)
            layout.addWidget(time_label)

class DateFrame(QFrame):
    def __init__(self, date: str, events: List[Event], config: CalendarConfig):
        super().__init__()
        self.config = config

        # DateFrame Properties
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.setMinimumSize(QSize(config.width, config.height))
        self.setMaximumSize(QSize(config.width, config.height))

        # Layout
        self.layout_ = QVBoxLayout()
        self.layout_.setContentsMargins(2, 2, 2, 2)
        self.setLayout(self.layout_)

        # Header with date info
        header = QHBoxLayout()
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        self.dom_label = QLabel(str(date_obj.day))
        self.dow_label = QLabel(date_obj.strftime('%a'))
        header_style = f"""
            font-family: {self.config.font};
            font-size: {self.config.font_size + 2}px;
            font-weight: bold;
            color: black;
        """
        self.dom_label.setStyleSheet(header_style)
        self.dow_label.setStyleSheet(header_style)
        header.addWidget(self.dom_label)
        header.addStretch()
        header.addWidget(self.dow_label)
        self.layout_.addLayout(header)

        # Events container
        self.events_layout = QVBoxLayout()
        self.layout_.addLayout(self.events_layout)

        self.update_events(events)

    def update_events(self, events: List[Event]):
        """Update the events displayed in this frame"""
        # Clear existing events
        while self.events_layout.count():
            item = self.events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new events
        for event in events:
            event_widget = EventWidget(event, self.config.font, self.config.font_size)
            self.events_layout.addWidget(event_widget)

        # Update background color
        is_active = datetime.now().strftime('%Y-%m-%d') == str(events[0].date) if events else False
        bg_color = self.config.color_scheme.active if is_active else self.config.color_scheme.inactive
        self.setStyleSheet(f"background-color: {bg_color};")

        self.events_layout.addStretch()

@dataclass
class CalendarCell:
    """Represents a cell in the calendar grid"""
    date: str
    widget: DateFrame
    events: List[Event]

class LegendWidget(QWidget):
    def __init__(self, color_scheme, config: CalendarConfig):
        super().__init__()
        self.layout_ = QHBoxLayout()
        self.layout_.setContentsMargins(5, 2, 5, 2)
        self.setLayout(self.layout_)
        self.styles = f"font-family: {config.font}; font-size: {config.font_size + 2}px;"
        self.update_legend({'Local': color_scheme.default})

    def update_legend(self, colors: Dict[str, str]):
        """Update legend with new color scheme"""
        while self.layout_.count():
            item = self.layout_.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for source, color in colors.items():
            color_box = QFrame()
            color_box.setFixedSize(20, 20)
            color_box.setStyleSheet(f"background-color: {color};")

            label = QLabel(source)
            label.setStyleSheet(f"color: {color}; " + self.styles)

            self.layout_.addWidget(color_box)
            self.layout_.addWidget(label)
            self.layout_.addSpacing(10)

        self.layout_.addStretch()

class GoogleCalendarLoader(QThread):
    events_loaded = pyqtSignal(dict)
    colors_loaded = pyqtSignal(dict)

    def __init__(self, g_sync: GoogleAuth, date_range: DateRange, update_interval: int = 300000):  # 5 minutes default
        super().__init__()
        self.g_sync = g_sync
        self.date_range = date_range
        self.update_interval = update_interval
        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_events)
        self.is_running = False

    def run(self):
        """Start periodic updates"""
        self.is_running = True
        self.fetch_events()
        self.timer.start(self.update_interval)

    def stop(self):
        """Stop periodic updates"""
        self.is_running = False
        self.timer.stop()

    def fetch_events(self):
        """Fetch events from Google Calendar"""
        if not self.is_running:
            return

        try:
            colors = self.g_sync.user_colors if self.g_sync.is_valid() else {}
            self.colors_loaded.emit(colors)

            gevents = self.g_sync.get_events(date_range=self.date_range)
            events_by_date: Dict[str, List[Event]] = {}
            for event in gevents:
                date_str = str(event.date)
                if date_str not in events_by_date:
                    events_by_date[date_str] = []
                events_by_date[date_str].append(event)
            self.events_loaded.emit(events_by_date)

        except Exception as e:
            print(f"Error fetching Google Calendar events: {e}")

class Calendar(HeadspaceWidget):

    def __init__(self):
        super().__init__()
        self.g_sync = GoogleAuth(self.filesystem.path)
        self.cal_config = CalendarConfig()

        calendar_filepath = self.filesystem / self.yaml.get("calendar_filename", "calendar.json")
        self.cal = JsonCalendar(calendar_filepath)

        self.current_events: Dict[str, List[Event]] = {}
        self.calendar_cells: Dict[str, CalendarCell] = {}
        self.google_loader: Optional[GoogleCalendarLoader] = None

        # Main layout
        self.layout_ = QVBoxLayout()
        self.setLayout(self.layout_)

        # Create and add legend
        self.legend = LegendWidget(self.cal_config.color_scheme, self.cal_config)
        self.layout_.addWidget(self.legend)

        # Create calendar grid
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(4)
        self.layout_.addLayout(self.calendar_grid)

    @property
    def date_range(self) -> DateRange:
        """Calculate the current date range for the calendar view."""
        today = datetime.now().date()
        prev_sunday = today - timedelta(days=today.weekday() + 1)
        prev_sunday_dt = datetime.combine(prev_sunday, datetime.min.time())
        return DateRange.from_start(prev_sunday_dt, days=self.cal_config.days, timezone=self.cal_config.tz)


    def render_calendar(self):
        """Render or update the calendar grid"""
        if self.cal_config.mode == 'week':
            for i, (date, events) in enumerate(self.current_events.items()):
                if date not in self.calendar_cells:
                    date_frame = DateFrame(date, events, self.cal_config)
                    self.calendar_cells[date] = CalendarCell(date, date_frame, events)
                    self.calendar_grid.addWidget(date_frame, i // 7, i % 7)
                else:
                    self.calendar_cells[date].events = events
                    self.calendar_cells[date].widget.update_events(events)
        elif self.cal_config.mode == 'day':
            self.logs.error("Calendar Mode Days has not been implemented. Please use Week mode.")
        else:
            self.logs.error(f"Calendar config setting cannot be determined Literal['week', 'day'] = {self.cal_config.mode}")

    def _update_calendar_contents(self):
        """Update contents of existing calendar cells"""
        for date, events in self.current_events.items():
            if date in self.calendar_cells:
                self.calendar_cells[date].widget.update_events(events)

    @pyqtSlot(dict)
    def _on_google_events_loaded(self, google_events: Dict[str, List[Event]]):
        """Handle Google Calendar events when they're loaded."""
        for date, events in google_events.items():
            if date in self.current_events:
                local_events = [e for e in self.current_events[date] if not hasattr(e, 'google_id')]
                self.current_events[date] = local_events + events
            else:
                self.current_events[date] = events

        self._update_calendar_contents()

    @pyqtSlot(dict)
    def _on_colors_loaded(self, colors: Dict[str, str]):
        """Handle updated color scheme from Google Calendar"""
        all_colors = {'Local': self.cal_config.color_scheme.default, **colors}
        self.legend.update_legend(all_colors)

    def google_sync(self):
        """Initialize and start Google Calendar synchronization"""
        if self.google_loader:
            self.google_loader.stop()
            self.google_loader.wait()

        self.google_loader = GoogleCalendarLoader(
            self.g_sync, 
            self.date_range,
            update_interval=self.cal_config.yaml.get("google_sync_interval", 300000)
        )
        self.google_loader.events_loaded.connect(self._on_google_events_loaded)
        self.google_loader.colors_loaded.connect(self._on_colors_loaded)
        self.google_loader.start()

    def render_widget(self):
        """Initial render with local calendar data."""
        dates = self.cal[ str(self.date_range.start.date()) : str(self.date_range.end.date()) ]

        self.current_events = self.cal.inflate_calendar_events(dates)

        self.render_calendar()

        if self.cal_config.g_synced and self.g_sync.is_valid():
            self.google_sync()

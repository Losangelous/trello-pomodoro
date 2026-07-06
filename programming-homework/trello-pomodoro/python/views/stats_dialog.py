import flet as ft
from datetime import date, timedelta

class StatsDialog(ft.AlertDialog):
    def __init__(self, pomodoro_service):
        super().__init__()
        self.pomodoro_service = pomodoro_service
        self.mode = "week"
        self.offset = 0
        self._build_content()

    def _build_content(self):
        mode_row = ft.Row([
            ft.ElevatedButton("周", on_click=lambda e: self._set_mode("week")),
            ft.ElevatedButton("月", on_click=lambda e: self._set_mode("month")),
        ], alignment=ft.MainAxisAlignment.CENTER)

        self.title_text = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
        nav_row = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=self._prev),
            self.title_text,
            ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=self._next),
        ], alignment=ft.MainAxisAlignment.CENTER)

        self.total_sessions = ft.Text("0", size=24, weight=ft.FontWeight.BOLD)
        self.total_minutes = ft.Text("0", size=24, weight=ft.FontWeight.BOLD)
        stats_row = ft.Row([
            ft.Card(content=ft.Container(ft.Column([ft.Text("总番茄数"), self.total_sessions]), padding=10)),
            ft.Card(content=ft.Container(ft.Column([ft.Text("总专注分钟"), self.total_minutes]), padding=10)),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)

        self.details = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)

        self.content = ft.Container(
            content=ft.Column([mode_row, nav_row, stats_row, ft.Divider(), self.details], spacing=10),
            width=500, height=500, padding=10
        )
        self.actions = [ft.TextButton("关闭", on_click=lambda e: setattr(self, 'open', False))]
        self._loaded = False

    def did_mount(self):
        self._load_data()
        self.update()

    def _set_mode(self, mode):
        self.mode = mode
        self.offset = 0
        if self._loaded:
            self._load_data()
            self.update()

    def _prev(self, e):
        self.offset -= 1
        if self._loaded:
            self._load_data()
            self.update()

    def _next(self, e):
        self.offset += 1
        if self._loaded:
            self._load_data()
            self.update()

    def _load_data(self):
        today = date.today()
        if self.mode == "week":
            start = today - timedelta(days=today.weekday()) + timedelta(weeks=self.offset)
            end = start + timedelta(days=6)
            self.title_text.value = f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"
            total_s, total_m = 0, 0
            items = []
            for i in range(7):
                d = start + timedelta(days=i)
                stats = self.pomodoro_service.get_daily_stats(d)
                c = stats.get("completed_sessions", 0)
                m = stats.get("total_focus_minutes", 0)
                total_s += c
                total_m += m
                items.append(ft.Text(f"{d.strftime('%a %m/%d')}: {c} 番茄, {m} 分钟"))
            self.total_sessions.value = str(total_s)
            self.total_minutes.value = str(total_m)
            self.details.controls = items
        else:  # month
            year = today.year
            month = today.month + self.offset
            while month < 1:
                month += 12
                year -= 1
            while month > 12:
                month -= 12
                year += 1
            first = date(year, month, 1)
            if month == 12:
                last = date(year+1, 1, 1) - timedelta(days=1)
            else:
                last = date(year, month+1, 1) - timedelta(days=1)
            self.title_text.value = first.strftime("%Y年%m月")
            total_s, total_m = 0, 0
            items = []
            d = first
            while d <= last:
                stats = self.pomodoro_service.get_daily_stats(d)
                c = stats.get("completed_sessions", 0)
                m = stats.get("total_focus_minutes", 0)
                total_s += c
                total_m += m
                items.append(ft.Text(f"{d.day}日: {c} 番茄, {m} 分钟"))
                d += timedelta(days=1)
            self.total_sessions.value = str(total_s)
            self.total_minutes.value = str(total_m)
            self.details.controls = items
        self._loaded = True
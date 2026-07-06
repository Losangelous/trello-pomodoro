import flet as ft
from services.pomodoro_service import PomodoroService
from services.board_service import BoardService
import threading
import time
import os
from views.stats_dialog import StatsDialog

class PomodoroView(ft.UserControl):
    def __init__(self, pomodoro_service: PomodoroService, board_service: BoardService):
        super().__init__()
        self.pomodoro_service = pomodoro_service
        self.board_service = board_service
        self.timer_thread = None
        self.running = False
        self.current_session = None
        self.remaining_seconds = 0
        self.current_card = None
        self.settings = self.pomodoro_service.get_settings()

    def build(self):
        top_row = ft.Row([
            ft.Text("🍅 番茄钟", size=24, weight=ft.FontWeight.BOLD, expand=True),
            ft.IconButton(ft.Icons.SETTINGS, tooltip="设置", on_click=self.open_settings),
            ft.IconButton(ft.Icons.BAR_CHART, tooltip="统计", on_click=self.show_stats),
        ])

        self.timer_text = ft.Text(f"{self.settings.get('focus_duration', 25):02d}:00", size=72, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
        self.status_text = ft.Text("准备开始", size=16, color=ft.Colors.GREY_600)
        self.progress_bar = ft.ProgressBar(width=350, value=0, color=ft.Colors.BLUE_700)
        self.start_btn = ft.ElevatedButton("开始专注", icon=ft.Icons.PLAY_ARROW, on_click=self.start_timer, width=160)
        self.pause_btn = ft.ElevatedButton("暂停", icon=ft.Icons.PAUSE, on_click=self.pause_timer, disabled=True, width=160)
        self.reset_btn = ft.IconButton(icon=ft.Icons.STOP, tooltip="停止并重置", on_click=self.reset_timer, icon_color=ft.Colors.RED_600)
        self.stats_text = ft.Text("今日完成: 0 个番茄", size=14)

        self.card_dropdown = ft.Dropdown(label="选择任务卡片", width=300, options=self.load_cards(), on_change=self.on_card_selected)
        self.refresh_btn = ft.IconButton(icon=ft.Icons.REFRESH, on_click=self.refresh_cards)

        self.card_title = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
        self.card_desc = ft.Text("", selectable=True)
        self.card_due_date = ft.Text("")
        self.attachments_list = ft.Column(spacing=5)
        self.card_info_panel = ft.Container(
            content=ft.Column([
                ft.Text("当前任务详情", size=18, weight=ft.FontWeight.BOLD),
                self.card_title,
                self.card_desc,
                self.card_due_date,
                ft.Text("附件", weight=ft.FontWeight.BOLD),
                self.attachments_list,
            ], spacing=10),
            padding=10,
            #bgcolor=ft.Colors.SURFACE_VARIANT,
            border_radius=10,
            visible=False,
            expand=True,
        )

        left_column = ft.Column([
            top_row,
            ft.Divider(),
            ft.Container(
                content=ft.Column([self.timer_text, self.status_text, self.progress_bar], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20, border_radius=10, bgcolor=ft.Colors.BLUE_50
            ),
            ft.Row([self.start_btn, self.pause_btn], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.reset_btn, self.stats_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Text("选择任务", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([self.card_dropdown, self.refresh_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], expand=1)

        main_row = ft.Row([left_column, self.card_info_panel], expand=True, spacing=20)
        return main_row

    def show_stats(self, e):
        dlg = StatsDialog(self.pomodoro_service)
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def load_cards(self):
        options = [ft.dropdown.Option("", "无特定任务")]
        boards = self.board_service.get_all_boards()
        for board in boards:
            for lst in board.get('lists', []):
                for card in lst.get('cards', []):
                    label = f"[{board['name']}] {card['title']}"
                    options.append(ft.dropdown.Option(card['id'], label))
        return options

    def refresh_cards(self, e=None):
        self.card_dropdown.options = self.load_cards()
        self.card_dropdown.update()
        self.update_stats()
        if self.card_dropdown.value:
            self.on_card_selected(None)

    def on_card_selected(self, e):
        card_id = self.card_dropdown.value
        if not card_id:
            self.card_info_panel.visible = False
            self.current_card = None
        else:
            self.current_card = self.board_service.get_card(card_id)
            if self.current_card:
                self.update_card_info()
                self.card_info_panel.visible = True
            else:
                self.card_info_panel.visible = False
        self.update()

    def update_card_info(self):
        if not self.current_card:
            return
        self.card_title.value = self.current_card.get("title", "")
        self.card_desc.value = self.current_card.get("description", "")
        due_date = self.current_card.get("due_date", "")
        self.card_due_date.value = f"截止日期: {due_date[:16] if due_date else '未设置'}"
        self.attachments_list.controls.clear()
        attachments = self.current_card.get("attachments", [])
        for att in attachments:
            row = ft.Row([
                ft.Icon(ft.Icons.ATTACH_FILE),
                ft.Text(att["original_filename"], expand=True),
                ft.IconButton(ft.Icons.DOWNLOAD, on_click=lambda e, f=att["filename"], name=att["original_filename"]: self._download(f, name)),
            ])
            ext = os.path.splitext(att["original_filename"])[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                row.controls.insert(2, ft.IconButton(ft.Icons.VISIBILITY, on_click=lambda e, f=att["filename"]: self._preview_image(f)))
            self.attachments_list.controls.append(row)
        self.update()

    def _download(self, filename, original_name):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(project_root, "data", "attachments")
        src = os.path.join(data_dir, filename)
        if os.path.exists(src):
            def save_result(e: ft.FilePickerResultEvent):
                if e.path:
                    import shutil
                    shutil.copyfile(src, e.path)
                    self.page.show_snack_bar(ft.SnackBar(ft.Text(f"已保存到 {e.path}")))
            if not hasattr(self, '_save_picker'):
                self._save_picker = ft.FilePicker(on_result=save_result)
                self.page.overlay.append(self._save_picker)
                self.page.update()
            self._save_picker.save_file(file_name=original_name)
        else:
            self.page.show_snack_bar(ft.SnackBar(ft.Text("文件不存在")))

    def _preview_image(self, filename):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(project_root, "data", "attachments")
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            img = ft.Image(src=file_path, fit=ft.ImageFit.CONTAIN, width=400, height=400)
            dlg = ft.AlertDialog(
                title=ft.Text("图片预览"),
                content=ft.Container(content=img, width=500, height=500),
                actions=[ft.TextButton("关闭", on_click=lambda e: setattr(dlg, 'open', False))]
            )
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
        else:
            self.page.show_snack_bar(ft.SnackBar(ft.Text("图片文件不存在")))

    def update_stats(self):
        stats = self.pomodoro_service.get_today_stats()
        completed = stats.get('completed_sessions', 0)
        self.stats_text.value = f"今日完成: {completed} 个番茄"
        self.update()

    def open_settings(self, e):
        self.settings = self.pomodoro_service.get_settings()
        focus_field = ft.TextField(label="专注时长 (分钟)", value=str(self.settings.get("focus_duration", 25)), keyboard_type=ft.KeyboardType.NUMBER)
        short_break_field = ft.TextField(label="短休息时长 (分钟)", value=str(self.settings.get("short_break_duration", 5)), keyboard_type=ft.KeyboardType.NUMBER)
        long_break_field = ft.TextField(label="长休息时长 (分钟)", value=str(self.settings.get("long_break_duration", 15)), keyboard_type=ft.KeyboardType.NUMBER)
        interval_field = ft.TextField(label="长休息间隔 (个番茄)", value=str(self.settings.get("long_break_interval", 4)), keyboard_type=ft.KeyboardType.NUMBER)

        def save(e):
            try:
                focus = int(focus_field.value)
                short = int(short_break_field.value)
                long_ = int(long_break_field.value)
                interval = int(interval_field.value)
                if not (1 <= focus <= 60):
                    self.page.show_snack_bar(ft.SnackBar(ft.Text("专注时长需在1-60分钟之间")))
                    return
                if not (1 <= short <= 15):
                    self.page.show_snack_bar(ft.SnackBar(ft.Text("短休息需在1-15分钟之间")))
                    return
                if not (1 <= long_ <= 30):
                    self.page.show_snack_bar(ft.SnackBar(ft.Text("长休息需在1-30分钟之间")))
                    return
                if not (2 <= interval <= 10):
                    self.page.show_snack_bar(ft.SnackBar(ft.Text("长休息间隔需在2-10之间")))
                    return
                self.pomodoro_service.update_settings(
                    focus_duration=focus,
                    short_break_duration=short,
                    long_break_duration=long_,
                    long_break_interval=interval
                )
                self.settings = self.pomodoro_service.get_settings()
                self.reset_timer(None)
                self.page.show_snack_bar(ft.SnackBar(ft.Text("设置已保存，下次计时生效")))
                dlg.open = False
                self.page.update()
            except ValueError:
                self.page.show_snack_bar(ft.SnackBar(ft.Text("请输入有效的数字")))

        dlg = ft.AlertDialog(
            title=ft.Text("番茄钟设置"),
            content=ft.Column([focus_field, short_break_field, long_break_field, interval_field], spacing=10, width=300),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dlg, 'open', False)),
                ft.TextButton("保存", on_click=save),
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def start_timer(self, e):
        if not self.running:
            card_id = self.card_dropdown.value or None
            card_title = ""
            if card_id and self.current_card:
                card_title = self.current_card.get("title", "")
            session_info = self.pomodoro_service.start_session(card_id, card_title)
            self.current_session = session_info
            self.remaining_seconds = session_info['duration_minutes'] * 60
            self.running = True
            self.start_btn.disabled = True
            self.pause_btn.disabled = False
            state = session_info['state']
            if state == 'focusing':
                self.status_text.value = "🔥 专注中..."
                self.status_text.color = ft.Colors.BLUE_700
            elif state == 'short_break':
                self.status_text.value = "☕ 短休息中..."
                self.status_text.color = ft.Colors.GREEN_700
            else:
                self.status_text.value = "🌙 长休息中..."
                self.status_text.color = ft.Colors.PURPLE_700
            self.update()
            self.timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
            self.timer_thread.start()

    def start_break(self, break_type):
        session_info = self.pomodoro_service.start_break(break_type)
        self.current_session = session_info
        self.remaining_seconds = session_info['duration_minutes'] * 60
        self.running = True
        self.start_btn.disabled = True
        self.pause_btn.disabled = False
        if break_type == "short":
            self.status_text.value = "☕ 短休息中..."
            self.status_text.color = ft.Colors.GREEN_700
        else:
            self.status_text.value = "🌙 长休息中..."
            self.status_text.color = ft.Colors.PURPLE_700
        self.update()
        self.timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.timer_thread.start()

    def pause_timer(self, e):
        if self.running:
            self.running = False
            self.pause_btn.text = "继续"
            self.pause_btn.icon = ft.Icons.PLAY_ARROW
            self.status_text.value = "⏸️ 已暂停"
            self.pomodoro_service.pause_session()
        else:
            self.running = True
            self.pause_btn.text = "暂停"
            self.pause_btn.icon = ft.Icons.PAUSE
            if self.current_session:
                state = self.current_session.get('state')
                if state == 'focusing':
                    self.status_text.value = "🔥 专注中..."
                elif state == 'short_break':
                    self.status_text.value = "☕ 短休息中..."
                else:
                    self.status_text.value = "🌙 长休息中..."
            self.pomodoro_service.resume_session()
            self.timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
            self.timer_thread.start()
        self.update()

    def reset_timer(self, e):
        self.running = False
        default_minutes = self.settings.get("focus_duration", 25)
        self.remaining_seconds = default_minutes * 60
        self.current_session = None
        self.timer_text.value = f"{default_minutes:02d}:00"
        self.progress_bar.value = 0
        self.status_text.value = "准备开始"
        self.status_text.color = ft.Colors.GREY_600
        self.start_btn.disabled = False
        self.pause_btn.disabled = True
        self.pause_btn.text = "暂停"
        self.pause_btn.icon = ft.Icons.PAUSE
        self.update()

    def timer_loop(self):
        while self.running and self.remaining_seconds > 0:
            time.sleep(1)
            if not self.running:
                break
            self.remaining_seconds -= 1
            minutes = self.remaining_seconds // 60
            seconds = self.remaining_seconds % 60
            def update():
                self.timer_text.value = f"{minutes:02d}:{seconds:02d}"
                if self.current_session:
                    total = self.current_session['duration_minutes'] * 60
                    progress = 1 - (self.remaining_seconds / total)
                    self.progress_bar.value = progress
                self.update()
            self.page.run_thread(update)
        if self.remaining_seconds <= 0:
            self.page.run_thread(self.timer_finished)

    def timer_finished(self):
        self.running = False
        self.start_btn.disabled = False
        self.pause_btn.disabled = True

        if self.current_session:
            # 停止当前会话
            self.pomodoro_service.stop_session(completed=True)
            self.update_stats()

            # 获取刚结束的会话类型
            session_state = self.current_session.get('state')
            if session_state == 'focusing':
                # 专注完成，决定下一个休息类型
                next_type, duration = self.pomodoro_service.get_next_session_type()
                dlg = ft.AlertDialog(
                    title=ft.Text("🎉 专注完成！"),
                    content=ft.Text(f"接下来休息 {duration} 分钟"),
                    actions=[ft.TextButton("开始休息", on_click=lambda e: self.start_break(next_type))]
                )
            else:
                # 休息完成，自动开始下一个专注（可选）
                focus_duration = self.settings.get("focus_duration", 25)
                dlg = ft.AlertDialog(
                    title=ft.Text("☕ 休息结束"),
                    content=ft.Text(f"开始下一个专注 {focus_duration} 分钟"),
                    actions=[ft.TextButton("开始专注", on_click=self.start_timer)]
                )
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
        else:
            self.reset_timer(None)

    def close_dialog(self, dlg):
        dlg.open = False
        self.page.update()
import flet as ft
from typing import Dict, List
from services.board_service import BoardService
from views.card_detail import CardDetailDialog
#from dark_theme import DarkTheme
import threading
import time

class BoardView(ft.UserControl):
    def __init__(self, board_id: str, board_service: BoardService, on_card_updated: callable = None):
        super().__init__()
        self.board_id = board_id
        self.board_service = board_service
        self.on_card_updated = on_card_updated
        self.lists: List[Dict] = []
        self.board_row = ft.Row(scroll="horizontal", spacing=20, vertical_alignment=ft.CrossAxisAlignment.START)
        self.drag_data = None

    def build(self):
        return ft.Column([self.board_row], expand=True)

    def did_mount(self):
        self.load_board()
        self.start_reminder_checker()

    def start_reminder_checker(self):
        def check_loop():
            while True:
                time.sleep(60)
                if self.page:
                    self.page.run_thread(self.check_reminders)
        threading.Thread(target=check_loop, daemon=True).start()

    def check_reminders(self):
        due_soon = self.board_service.get_due_soon_cards(minutes_before=15)
        overdue = self.board_service.get_overdue_cards()
        total = len(due_soon) + len(overdue)
        if total > 0 and self.page:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"你有 {total} 个任务即将到期或已过期"),
                    bgcolor=ft.Colors.ORANGE_600,
                    duration=5000
                )
            )

    def load_board(self):
        board = self.board_service.get_board(self.board_id)
        if board:
            self.lists = board.get("lists", [])
            self.update_ui()

    def update_ui(self):
        self.board_row.controls.clear()
        for lst in self.lists:
            list_widget = self._create_list_widget(lst)
            self.board_row.controls.append(list_widget)
        self.update()

    def refresh_by_theme(self):
        self.load_board()

    def _create_list_widget(self, lst: Dict) -> ft.Container:
        header = ft.Container(
            content=ft.Row([
                ft.Text(lst["name"], size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="删除列表",
                    on_click=lambda e, list_id=lst["id"]: self._confirm_delete_list(list_id),
                    icon_color=ft.Colors.RED_400
                ),
            ]),
            padding=10,
            #bgcolor=ft.Colors.GREY_100,
            border_radius=ft.border_radius.only(top_left=8, top_right=8)
        )

        cards_column = ft.Column(spacing=10, controls=[], data={"list_id": lst["id"]})
        for card in lst.get("cards", []):
            card_control = self._create_card_widget(card, lst["id"])
            cards_column.controls.append(card_control)

        add_btn = ft.TextButton("+ 添加卡片", icon=ft.Icons.ADD,
                                on_click=lambda e, list_id=lst["id"]: self._show_add_card_dialog(list_id))
        
        list_container = ft.Container(
            content=ft.Column([
                header,
                ft.Container(content=cards_column, padding=10),
                add_btn
            ]),
            width=320,
            bgcolor=ft.Colors.SURFACE,
            border_radius=8,
            ##这里要改成color参数随深浅色模式而变化
            
            shadow=ft.BoxShadow(blur_radius=4,color=ft.Colors.GREY_400)
            
        ) 
        return list_container

    def _create_card_widget(self, card: Dict, list_id: str) -> ft.GestureDetector:
        due_date = card.get("due_date")
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK

        if is_dark:
            normal_bg = ft.Colors.GREY_800  # 深色模式用深灰色
        else:
            normal_bg = ft.Colors.BLUE_50   # 浅色模式用浅蓝色
        bg_color = ft.Colors.BLUE_50
        if due_date:
            from datetime import datetime
            due = datetime.fromisoformat(due_date)
            now = datetime.now()
            if due < now:
                bg_color = ft.Colors.RED_100
            elif (due - now).total_seconds() < 24 * 3600:
                bg_color = ft.Colors.ORANGE_100
            else:
                bg_color=normal_bg
        else:
            bg_color=normal_bg

        card_content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(card["title"], weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_size=16,
                        tooltip="删除卡片",
                        on_click=lambda e, cid=card["id"]: self._delete_card(cid, list_id),
                        icon_color=ft.Colors.RED_400
                    ),
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=16, color=ft.Colors.GREEN),
                    ft.Text(f"{card.get('pomodoro_count',0)} 番茄"),
                    ft.Icon(ft.Icons.ATTACH_FILE, size=16, color=ft.Colors.GREY) if card.get("attachments") else ft.Container()
                ], spacing=10)
            ]),
            padding=10,
            bgcolor=bg_color,
            border_radius=6,
        )

        gd = ft.GestureDetector(
            content=card_content,
            on_pan_start=lambda e, cid=card["id"], lid=list_id: self._on_card_pan_start(e, cid, lid),
            on_pan_update=self._on_card_pan_update,
            on_pan_end=self._on_card_pan_end,
            on_tap=lambda e, c=card: self._open_card_detail(c),
        )
        return gd

    def _on_card_pan_start(self, e: ft.DragStartEvent, card_id: str, list_id: str):
        self.drag_data = {"card_id": card_id, "source_list_id": list_id}

    def _on_card_pan_update(self, e: ft.DragUpdateEvent):
        pass

    def _on_card_pan_end(self, e: ft.DragEndEvent):
        if not self.drag_data:
            return
        card_id = self.drag_data["card_id"]
        src_list_id = self.drag_data["source_list_id"]

        def on_move(e):
            option_dlg.open = False
            self._show_move_to_list_menu(card_id, src_list_id)

        def on_sort(e):
            option_dlg.open = False
            self._show_reorder_menu(card_id, src_list_id)

        option_dlg = ft.AlertDialog(
            title=ft.Text("拖拽操作"),
            content=ft.Text("请选择操作："),
            actions=[
                ft.TextButton("移动到其他列表", on_click=on_move),
                ft.TextButton("在当前列表排序", on_click=on_sort),
                ft.TextButton("取消", on_click=lambda e: setattr(option_dlg, 'open', False)),
            ]
        )
        self.page.dialog = option_dlg
        option_dlg.open = True
        self.page.update()

        self.drag_data = None

    def _show_move_to_list_menu(self, card_id: str, src_list_id: str):
        target_options = [ft.dropdown.Option(lst["id"], lst["name"]) for lst in self.lists if lst["id"] != src_list_id]
        if not target_options:
            self.page.show_snack_bar(ft.SnackBar(ft.Text("没有其他列表可移动")))
            return
        target_dropdown = ft.Dropdown(label="选择目标列表", options=target_options, width=200)
        def move_to_target(e):
            target_id = target_dropdown.value
            if target_id:
                self.board_service.move_card(card_id, target_id)
                self.load_board()
            dlg.open = False
        dlg = ft.AlertDialog(
            title=ft.Text("移动卡片"),
            content=target_dropdown,
            actions=[
                ft.TextButton("移动", on_click=move_to_target),
                ft.TextButton("取消", on_click=lambda e: setattr(dlg, 'open', False)),
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _show_reorder_menu(self, card_id: str, list_id: str):
        target_list = None
        for lst in self.lists:
            if lst["id"] == list_id:
                target_list = lst
                break
        if not target_list:
            return
        cards = target_list.get("cards", [])
        card_ids = [c["id"] for c in cards]
        try:
            current_index = card_ids.index(card_id)
        except ValueError:
            return

        def move_up(e):
            if current_index > 0:
                new_order = card_ids.copy()
                new_order[current_index], new_order[current_index-1] = new_order[current_index-1], new_order[current_index]
                self.board_service.reorder_cards(list_id, new_order)
                self.load_board()
            dlg.open = False
        def move_down(e):
            if current_index < len(card_ids)-1:
                new_order = card_ids.copy()
                new_order[current_index], new_order[current_index+1] = new_order[current_index+1], new_order[current_index]
                self.board_service.reorder_cards(list_id, new_order)
                self.load_board()
            dlg.open = False
        def move_top(e):
            if current_index > 0:
                new_order = [card_id] + [cid for cid in card_ids if cid != card_id]
                self.board_service.reorder_cards(list_id, new_order)
                self.load_board()
            dlg.open = False
        def move_bottom(e):
            if current_index < len(card_ids)-1:
                new_order = [cid for cid in card_ids if cid != card_id] + [card_id]
                self.board_service.reorder_cards(list_id, new_order)
                self.load_board()
            dlg.open = False

        dlg = ft.AlertDialog(
            title=ft.Text("排序卡片"),
            content=ft.Column([
                ft.Text("选择移动方向："),
                ft.Row([ft.TextButton("置顶", on_click=move_top), ft.TextButton("上移", on_click=move_up)]),
                ft.Row([ft.TextButton("下移", on_click=move_down), ft.TextButton("置底", on_click=move_bottom)]),
            ]),
            actions=[ft.TextButton("取消", on_click=lambda e: setattr(dlg, 'open', False))],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _delete_card(self, card_id: str, list_id: str):
        def confirm(e):
            self.board_service.delete_card(card_id, permanent=False)
            self.load_board()
            dialog.open = False
            self.page.update()
        dialog = ft.AlertDialog(
            title=ft.Text("删除卡片"),
            content=ft.Text("确定要将此卡片移至归档吗？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False)),
                ft.TextButton("确定", on_click=confirm),
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _confirm_delete_list(self, list_id: str):
        def confirm(e):
            self.board_service.delete_list(list_id)
            self.load_board()
            dialog.open = False
            self.page.update()
        dialog = ft.AlertDialog(
            title=ft.Text("删除列表"),
            content=ft.Text("删除列表会将其中的所有卡片归档，是否继续？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False)),
                ft.TextButton("确定", on_click=confirm),
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _show_add_card_dialog(self, list_id: str):
        title_field = ft.TextField(label="卡片标题", autofocus=True)
        def add(e):
            title = title_field.value.strip()
            if title:
                self.board_service.create_card(list_id, title)
                self.load_board()
                dialog.open = False
                self.page.update()
        dialog = ft.AlertDialog(
            title=ft.Text("新建卡片"),
            content=title_field,
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False)),
                ft.TextButton("创建", on_click=add),
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _open_card_detail(self, card: Dict):
        def on_update():
            self.load_board()
            if self.on_card_updated:
                self.on_card_updated()
        dlg = CardDetailDialog(card["id"], self.board_service, on_update)
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
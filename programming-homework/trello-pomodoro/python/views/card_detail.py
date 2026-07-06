import flet as ft
from services.board_service import BoardService
import os
import shutil
import uuid
from datetime import datetime

class CardDetailDialog(ft.AlertDialog):
    def __init__(self, card_id: str, board_service: BoardService, on_update: callable):
        super().__init__()
        self.card_id = card_id
        self.board_service = board_service
        self.on_update = on_update
        self.card_data = None
        self.attachments = []
        self.attachments_list = ft.Column()
        self._loaded = False
        self._load_card()

    def _is_image(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

    def _load_card(self):
        self.card_data = self.board_service.get_card(self.card_id)
        if self.card_data:
            self.attachments = self.card_data.get("attachments", [])
            self._build_content()

    def _build_content(self):
        title_field = ft.TextField(label="标题", value=self.card_data["title"])
        desc_field = ft.TextField(label="备注", value=self.card_data.get("description", ""), multiline=True, min_lines=3)
        due_date_str = self.card_data.get("due_date", "")
        due_field = ft.TextField(label="截止日期 (YYYY-MM-DD HH:MM)", value=due_date_str[:16] if due_date_str else "")
        reminder_minutes = ft.Dropdown(
            label="提前提醒",
            options=[
                ft.dropdown.Option("15", "15分钟"),
                ft.dropdown.Option("60", "1小时"),
                ft.dropdown.Option("1440", "1天"),
            ],
            value=str(self.card_data.get("reminder_minutes", 15))
        )

        self._refresh_attachments(update=False)
        upload_btn = ft.ElevatedButton("上传文件", icon=ft.Icons.UPLOAD_FILE, on_click=self._upload_file)
        delete_card_btn = ft.ElevatedButton("彻底删除卡片", icon=ft.Icons.DELETE_FOREVER, on_click=self._confirm_delete_card, bgcolor=ft.Colors.RED_100)

        content = ft.Column([
            title_field,
            desc_field,
            due_field,
            reminder_minutes,
            ft.Text("附件", weight=ft.FontWeight.BOLD),
            upload_btn,
            self.attachments_list,
            delete_card_btn,
        ], spacing=15, scroll=ft.ScrollMode.AUTO)

        self.content = content
        self.actions = [
            ft.TextButton("取消", on_click=self.close_dlg),
            ft.TextButton("保存", on_click=lambda e: self._save(title_field.value, desc_field.value, due_field.value, int(reminder_minutes.value)))
        ]
        self._loaded = True

    def _refresh_attachments(self, update=True):
        self.attachments_list.controls.clear()
        for att in self.attachments:
            filename = att["original_filename"]
            buttons = [
                ft.IconButton(ft.Icons.DOWNLOAD, on_click=lambda e, f=att["filename"], name=filename: self._download(f, name)),
                ft.IconButton(ft.Icons.DELETE, on_click=lambda e, aid=att["id"]: self._delete_attachment(aid))
            ]
            if self._is_image(filename):
                buttons.insert(0, ft.IconButton(ft.Icons.VISIBILITY, on_click=lambda e, f=att["filename"]: self._preview_image(f)))
            row = ft.Row([
                ft.Icon(ft.Icons.ATTACH_FILE),
                ft.Text(filename, expand=True),
                ft.Row(buttons, spacing=5)
            ])
            self.attachments_list.controls.append(row)
        if update and self.page and self._loaded:
            self.update()

    def _preview_image(self, filename):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(project_root, "data", "attachments")
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            # 创建预览对话框
            img = ft.Image(src=file_path, fit=ft.ImageFit.CONTAIN, width=400, height=400)
            preview_dlg = ft.AlertDialog(
                title=ft.Text("图片预览"),
                content=ft.Container(content=img, width=500, height=500),
                actions=[ft.TextButton("关闭", on_click=lambda e: setattr(preview_dlg, 'open', False))]
            )
            self.page.dialog = preview_dlg
            preview_dlg.open = True
            self.page.update()
        else:
            self.page.show_snack_bar(ft.SnackBar(ft.Text("图片文件不存在")))

    def _upload_file(self, e):
        def pick_result(e: ft.FilePickerResultEvent):
            if e.files:
                file_path = e.files[0].path
                original_name = os.path.basename(file_path)
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                data_dir = os.path.join(project_root, "data", "attachments")
                os.makedirs(data_dir, exist_ok=True)
                ext = os.path.splitext(original_name)[1]
                new_filename = f"{uuid.uuid4().hex}{ext}"
                dest = os.path.join(data_dir, new_filename)
                shutil.copyfile(file_path, dest)
                size = os.path.getsize(dest)
                att = self.board_service.add_attachment(self.card_id, new_filename, original_name, size)
                if att:
                    self._load_card()
                    self._refresh_attachments()
                    self.page.show_snack_bar(ft.SnackBar(ft.Text("上传成功")))
                else:
                    self.page.show_snack_bar(ft.SnackBar(ft.Text("上传失败")))
        if not hasattr(self, '_file_picker'):
            self._file_picker = ft.FilePicker(on_result=pick_result)
            self.page.overlay.append(self._file_picker)
            self.page.update()
        self._file_picker.pick_files(allow_multiple=False)

    def _download(self, filename, original_name):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(project_root, "data", "attachments")
        src = os.path.join(data_dir, filename)
        if os.path.exists(src):
            def save_result(e: ft.FilePickerResultEvent):
                if e.path:
                    shutil.copyfile(src, e.path)
                    self.page.show_snack_bar(ft.SnackBar(ft.Text(f"已保存到 {e.path}")))
            if not hasattr(self, '_save_picker'):
                self._save_picker = ft.FilePicker(on_result=save_result)
                self.page.overlay.append(self._save_picker)
                self.page.update()
            self._save_picker.save_file(file_name=original_name)
        else:
            self.page.show_snack_bar(ft.SnackBar(ft.Text("文件不存在")))

    def _delete_attachment(self, attachment_id):
        att = next((a for a in self.attachments if a["id"] == attachment_id), None)
        if att:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(project_root, "data", "attachments")
            file_path = os.path.join(data_dir, att["filename"])
            if os.path.exists(file_path):
                os.remove(file_path)
        if self.board_service.remove_attachment(self.card_id, attachment_id):
            self._load_card()
            self._refresh_attachments()
            self.page.show_snack_bar(ft.SnackBar(ft.Text("删除成功")))
        else:
            self.page.show_snack_bar(ft.SnackBar(ft.Text("删除失败")))

    def _confirm_delete_card(self, e):
        def confirm_delete(e):
            self.board_service.delete_card(self.card_id, permanent=True)
            self.on_update()
            self.close_dlg(None)
        dlg = ft.AlertDialog(
            title=ft.Text("彻底删除卡片"),
            content=ft.Text("此操作不可恢复，确定要彻底删除该卡片吗？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dlg, 'open', False)),
                ft.TextButton("确定", on_click=confirm_delete),
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _save(self, title, description, due_date_str, reminder_minutes):
        update_data = {"title": title, "description": description, "reminder_minutes": reminder_minutes}
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str)
                update_data["due_date"] = due_date
            except:
                pass
        self.board_service.update_card(self.card_id, **update_data)
        self.on_update()
        self.close_dlg(None)

    def close_dlg(self, e):
        self.open = False
        self.page.update()
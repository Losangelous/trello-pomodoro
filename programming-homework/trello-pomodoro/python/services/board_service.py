from datetime import datetime
from typing import List, Optional, Dict
from storage.json_storage import JsonStorage
from models.board import Board, BoardList, Card, Label, ChecklistItem

class BoardService:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    # === Board Operations ===
    def get_all_boards(self) -> List[Dict]:
        return [board.to_dict() for board in self.storage.get_all_boards()]

    def get_board(self, board_id: str) -> Optional[Dict]:
        board = self.storage.get_board(board_id)
        return board.to_dict() if board else None

    def create_board(self, name: str, background_color: str = "#f5f5f5") -> Dict:
        board = self.storage.create_board(name, background_color)
        return board.to_dict()

    def update_board(self, board_id: str, name: str = None, background_color: str = None) -> Optional[Dict]:
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if background_color is not None:
            kwargs["background_color"] = background_color
        board = self.storage.update_board(board_id, **kwargs)
        return board.to_dict() if board else None

    def delete_board(self, board_id: str) -> bool:
        return self.storage.delete_board(board_id)

    # === List Operations ===
    def create_list(self, board_id: str, name: str, position: int = None) -> Optional[Dict]:
        board_list = self.storage.create_list(board_id, name, position)
        return board_list.to_dict() if board_list else None

    def update_list(self, list_id: str, **kwargs) -> Optional[Dict]:
        board_list = self.storage.update_list(list_id, **kwargs)
        return board_list.to_dict() if board_list else None

    def delete_list(self, list_id: str) -> bool:
        return self.storage.delete_list(list_id)

    def reorder_lists(self, board_id: str, list_ids: List[str]) -> bool:
        board = self.storage.get_board(board_id)
        if not board:
            return False
        for i, lid in enumerate(list_ids):
            for lst in board.lists:
                if lst.id == lid:
                    lst.position = i
                    break
        self.storage._save_boards()
        return True

    # === Card Operations ===
    def get_card(self, card_id: str) -> Optional[Dict]:
        card = self.storage.get_card(card_id)
        return card.to_dict() if card else None

    def create_card(self, list_id: str, title: str, **kwargs) -> Optional[Dict]:
        card = self.storage.create_card(list_id, title, **kwargs)
        return card.to_dict() if card else None

    def update_card(self, card_id: str, **kwargs) -> Optional[Dict]:
        card = self.storage.update_card(card_id, **kwargs)
        return card.to_dict() if card else None

    def move_card(self, card_id: str, target_list_id: str, target_position: int = None) -> Optional[Dict]:
        # 直接调用 storage.update_card 改变 list_id
        card = self.storage.update_card(card_id, list_id=target_list_id)
        if not card:
            return None
        # 如果需要指定位置，再更新一次 position
        if target_position is not None:
            card = self.storage.update_card(card_id, position=target_position)
        return card.to_dict() if card else None

    def delete_card(self, card_id: str, permanent: bool = False) -> bool:
        return self.storage.delete_card(card_id, permanent)

    def archive_card(self, card_id: str) -> bool:
        return self.storage.archive_card(card_id)

    def restore_card(self, card_id: str) -> bool:
        return self.storage.restore_card(card_id)

    def reorder_cards(self, list_id: str, card_ids: List[str]) -> bool:
        for board in self.storage.get_all_boards():
            for lst in board.lists:
                if lst.id == list_id:
                    for i, cid in enumerate(card_ids):
                        for card in lst.cards:
                            if card.id == cid:
                                card.position = i
                                break
                    self.storage._save_boards()
                    return True
        return False

    # === Checklist ===
    def add_checklist_item(self, card_id: str, text: str) -> Optional[Dict]:
        card = self.storage.get_card(card_id)
        if not card:
            return None
        card.checklist.append(ChecklistItem(text=text))
        card = self.storage.update_card(card_id, checklist=[
            {"id": i.id, "text": i.text, "completed": i.completed} for i in card.checklist
        ])
        return card.to_dict() if card else None

    def toggle_checklist_item(self, card_id: str, item_id: str) -> Optional[Dict]:
        card = self.storage.get_card(card_id)
        if not card:
            return None
        for item in card.checklist:
            if item.id == item_id:
                item.completed = not item.completed
                break
        card = self.storage.update_card(card_id, checklist=[
            {"id": i.id, "text": i.text, "completed": i.completed} for i in card.checklist
        ])
        return card.to_dict() if card else None

    def remove_checklist_item(self, card_id: str, item_id: str) -> Optional[Dict]:
        card = self.storage.get_card(card_id)
        if not card:
            return None
        card.checklist = [i for i in card.checklist if i.id != item_id]
        card = self.storage.update_card(card_id, checklist=[
            {"id": i.id, "text": i.text, "completed": i.completed} for i in card.checklist
        ])
        return card.to_dict() if card else None

    # === Label ===
    def create_label(self, board_id: str, name: str, color: str) -> Optional[Dict]:
        label = self.storage.create_label(board_id, name, color)
        return {"id": label.id, "name": label.name, "color": label.color} if label else None

    def update_label(self, label_id: str, name: str = None, color: str = None) -> Optional[Dict]:
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if color is not None:
            kwargs["color"] = color
        label = self.storage.update_label(label_id, **kwargs)
        return {"id": label.id, "name": label.name, "color": label.color} if label else None

    def delete_label(self, label_id: str) -> bool:
        return self.storage.delete_label(label_id)

    def add_label_to_card(self, card_id: str, label_id: str) -> Optional[Dict]:
        card = self.storage.get_card(card_id)
        if not card:
            return None
        if label_id not in card.labels:
            card.labels.append(label_id)
        card = self.storage.update_card(card_id, labels=card.labels)
        return card.to_dict() if card else None

    def remove_label_from_card(self, card_id: str, label_id: str) -> Optional[Dict]:
        card = self.storage.get_card(card_id)
        if not card:
            return None
        if label_id in card.labels:
            card.labels.remove(label_id)
        card = self.storage.update_card(card_id, labels=card.labels)
        return card.to_dict() if card else None

    # === Pin ===
    def pin_card(self, card_id: str) -> Optional[Dict]:
        return self.update_card(card_id, is_pinned=True)

    def unpin_card(self, card_id: str) -> Optional[Dict]:
        return self.update_card(card_id, is_pinned=False)

    # === Search ===
    def search(self, query: str, board_id: str = None) -> List[Dict]:
        results = []
        q = query.lower()
        boards = [self.storage.get_board(board_id)] if board_id else self.storage.get_all_boards()
        for board in boards:
            if not board:
                continue
            for lst in board.lists:
                for card in lst.cards:
                    if (q in card.title.lower() or q in card.description.lower() or
                        any(q in item.text.lower() for item in card.checklist)):
                        results.append(card.to_dict())
        results.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
        return results

    # === Due date and reminder ===
    def get_overdue_cards(self) -> List[Dict]:
        from datetime import datetime
        now = datetime.now()
        result = []
        for board in self.storage.get_all_boards():
            for lst in board.lists:
                for card in lst.cards:
                    if card.due_date and card.due_date < now and not card.is_archived:
                        result.append(card.to_dict())
        return result

    def get_today_due_cards(self) -> List[Dict]:
        from datetime import date
        today = date.today()
        result = []
        for board in self.storage.get_all_boards():
            for lst in board.lists:
                for card in lst.cards:
                    if card.due_date and card.due_date.date() == today and not card.is_archived:
                        result.append(card.to_dict())
        return result

    def get_due_soon_cards(self, minutes_before: int = 15) -> List[Dict]:
        from datetime import datetime, timedelta
        now = datetime.now()
        threshold = now + timedelta(minutes=minutes_before)
        result = []
        for board in self.storage.get_all_boards():
            for lst in board.lists:
                for card in lst.cards:
                    if card.due_date and not card.is_archived and now <= card.due_date <= threshold:
                        result.append(card.to_dict())
        return result

    # === Attachment Operations ===
    def add_attachment(self, card_id: str, filename: str, original_filename: str, size: int) -> Optional[Dict]:
        card = self.storage.get_card(card_id)
        if not card:
            return None
        import uuid
        attachment = {
            "id": str(uuid.uuid4()),
            "filename": filename,
            "original_filename": original_filename,
            "size": size,
            "uploaded_at": datetime.now().isoformat()
        }
        attachments = card.attachments.copy()
        attachments.append(attachment)
        updated = self.update_card(card_id, attachments=attachments)
        return attachment if updated else None

    def remove_attachment(self, card_id: str, attachment_id: str) -> bool:
        card = self.storage.get_card(card_id)
        if not card:
            return False
        attachments = [att for att in card.attachments if att["id"] != attachment_id]
        if len(attachments) == len(card.attachments):
            return False
        self.update_card(card_id, attachments=attachments)
        return True
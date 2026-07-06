import json
import os
from typing import Dict, List, Optional
from datetime import datetime, date
from pathlib import Path

from models.board import Board, BoardList, Card, ChecklistItem, Label
from models.pomodoro import PomodoroSettings, PomodoroSession, DailyStats

class JsonStorage:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.boards_file = self.data_dir / "boards.json"
        self.pomodoro_file = self.data_dir / "pomodoro.json"
        self.settings_file = self.data_dir / "settings.json"
        
        self._boards: Dict[str, Board] = {}
        self._sessions: List[PomodoroSession] = []
        self._pomodoro_settings = PomodoroSettings()
        self._daily_stats: Dict[str, DailyStats] = {}
        
        self._load_all()
    
    def _load_all(self):
        self._load_boards()
        self._load_pomodoro()
        self._load_settings()
    
    def _load_boards(self):
        if not self.boards_file.exists():
            # 创建默认看板
            default_board = Board(name="我的任务看板")
            default_lists = [
                BoardList(name="待办", board_id=default_board.id, position=0),
                BoardList(name="进行中", board_id=default_board.id, position=1),
                BoardList(name="已完成", board_id=default_board.id, position=2)
            ]
            default_board.lists = default_lists
            self._boards[default_board.id] = default_board
            self._save_boards()
            return
        
        try:
            with open(self.boards_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for board_data in data.get("boards", []):
                board = self._dict_to_board(board_data)
                self._boards[board.id] = board
        except Exception as e:
            print(f"加载看板数据失败: {e}")
            self._boards = {}
    
    def _save_boards(self):
        data = {
            "boards": [
                {
                    "id": board.id,
                    "name": board.name,
                    "background_color": board.background_color,
                    "lists": self._lists_to_dict(board.lists),
                    "labels": [{"id": l.id, "name": l.name, "color": l.color} for l in board.labels],
                    "archived_cards": [card.to_dict() for card in board.archived_cards],
                    "created_at": board.created_at.isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                for board in self._boards.values()
            ]
        }
        
        with open(self.boards_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _lists_to_dict(self, lists: List[BoardList]) -> List[Dict]:
        result = []
        for list_obj in lists:
            list_dict = {
                "id": list_obj.id,
                "name": list_obj.name,
                "board_id": list_obj.board_id,
                "position": list_obj.position,
                "default_template": list_obj.default_template,
                "auto_archive": list_obj.auto_archive,
                "cards": [card.to_dict() for card in list_obj.cards]
            }
            result.append(list_dict)
        return result
    
    def _dict_to_board(self, data: Dict) -> Board:
        board = Board(
            id=data["id"],
            name=data["name"],
            background_color=data.get("background_color", "#f5f5f5"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data.get("updated_at", data["created_at"]))
        )
        
        # 加载标签
        for label_data in data.get("labels", []):
            label = Label(id=label_data["id"], name=label_data["name"], color=label_data["color"])
            board.labels.append(label)
        
        # 加载列表
        for list_data in data.get("lists", []):
            board_list = BoardList(
                id=list_data["id"],
                name=list_data["name"],
                board_id=list_data["board_id"],
                position=list_data.get("position", 0),
                default_template=list_data.get("default_template", []),
                auto_archive=list_data.get("auto_archive", "never")
            )
            
            # 加载卡片
            for card_data in list_data.get("cards", []):
                card = self._dict_to_card(card_data)
                card.list_id = board_list.id
                board_list.cards.append(card)
            
            board.lists.append(board_list)
        
        # 加载归档卡片
        for card_data in data.get("archived_cards", []):
            card = self._dict_to_card(card_data)
            board.archived_cards.append(card)
        
        return board
    
    def _dict_to_card(self, data: Dict) -> Card:
        due_date = None
        if data.get("due_date"):
            due_date = datetime.fromisoformat(data["due_date"])
        
        checklist = []
        for item_data in data.get("checklist", []):
            item = ChecklistItem(
                id=item_data["id"],
                text=item_data["text"],
                completed=item_data["completed"]
            )
            checklist.append(item)
        
        return Card(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            list_id=data.get("list_id", ""),
            position=data.get("position", 0),
            due_date=due_date,
            reminder_minutes=data.get("reminder_minutes", 15),
            labels=data.get("labels", []),
            checklist=checklist,
            attachments=data.get("attachments", []),
            is_pinned=data.get("is_pinned", False),
            is_archived=data.get("is_archived", False),
            pomodoro_count=data.get("pomodoro_count", 0),
            total_focus_minutes=data.get("total_focus_minutes", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data.get("updated_at", data["created_at"]))
        )
    
    def _load_pomodoro(self):
        if not self.pomodoro_file.exists():
            return
        
        try:
            with open(self.pomodoro_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载专注记录
            for session_data in data.get("sessions", []):
                session = self._dict_to_session(session_data)
                self._sessions.append(session)
            
            # 加载每日统计
            for date_str, stats_data in data.get("daily_stats", {}).items():
                stats = DailyStats(
                    stats_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                    total_sessions=stats_data["total_sessions"],
                    completed_sessions=stats_data["completed_sessions"],
                    total_focus_minutes=stats_data["total_focus_minutes"],
                    sessions_by_card=stats_data.get("sessions_by_card", {})
                )
                self._daily_stats[date_str] = stats
        except Exception as e:
            print(f"加载番茄钟数据失败: {e}")
    
    def _save_pomodoro(self):
        data = {
            "sessions": [s.to_dict() for s in self._sessions],
            "daily_stats": {k: v.to_dict() for k, v in self._daily_stats.items()}
        }
        
        with open(self.pomodoro_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _dict_to_session(self, data: Dict) -> PomodoroSession:
        start_time = None
        end_time = None
        
        if data.get("start_time"):
            start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            end_time = datetime.fromisoformat(data["end_time"])
        
        return PomodoroSession(
            id=data["id"],
            card_id=data.get("card_id"),
            card_title=data.get("card_title", ""),
            state=self._str_to_timer_state(data.get("state", "idle")),
            start_time=start_time,
            end_time=end_time,
            duration_minutes=data.get("duration_minutes", 25),
            completed=data.get("completed", False),
            interrupted=data.get("interrupted", False),
            interruption_reason=data.get("interruption_reason", ""),
            created_at=datetime.fromisoformat(data["created_at"])
        )
    
    def _str_to_timer_state(self, state_str: str):
        from models.pomodoro import TimerState
        try:
            return TimerState(state_str)
        except:
            return TimerState.IDLE
    
    def _load_settings(self):
        if not self.settings_file.exists():
            self._pomodoro_settings = PomodoroSettings()
            return
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._pomodoro_settings = PomodoroSettings(
                focus_duration=data.get("focus_duration", 25),
                short_break_duration=data.get("short_break_duration", 5),
                long_break_duration=data.get("long_break_duration", 15),
                long_break_interval=data.get("long_break_interval", 4),
                enable_sound=data.get("enable_sound", True),
                sound_type=data.get("sound_type", "bell"),
                enable_notification=data.get("enable_notification", True)
            )
        except Exception as e:
            print(f"加载设置失败: {e}")
            self._pomodoro_settings = PomodoroSettings()
    
    def _save_settings(self):
        data = self._pomodoro_settings.to_dict()
        
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # === Board API ===
    def get_all_boards(self) -> List[Board]:
        return list(self._boards.values())
    
    def get_board(self, board_id: str) -> Optional[Board]:
        return self._boards.get(board_id)
    
    def create_board(self, name: str, background_color: str = "#f5f5f5") -> Board:
        board = Board(name=name, background_color=background_color)
        
        # 创建默认列表
        default_lists = [
            BoardList(name="待办", board_id=board.id, position=0),
            BoardList(name="进行中", board_id=board.id, position=1),
            BoardList(name="已完成", board_id=board.id, position=2)
        ]
        board.lists = default_lists
        
        self._boards[board.id] = board
        self._save_boards()
        return board
    
    def update_board(self, board_id: str, **kwargs) -> Optional[Board]:
        board = self._boards.get(board_id)
        if not board:
            return None
        
        if "name" in kwargs:
            board.name = kwargs["name"]
        if "background_color" in kwargs:
            board.background_color = kwargs["background_color"]
        
        board.updated_at = datetime.now()
        self._save_boards()
        return board
    
    def delete_board(self, board_id: str) -> bool:
        if board_id in self._boards:
            del self._boards[board_id]
            self._save_boards()
            return True
        return False
    
    # === List API ===
    def create_list(self, board_id: str, name: str, position: int = None) -> Optional[BoardList]:
        board = self._boards.get(board_id)
        if not board:
            return None
        
        if position is None:
            position = len(board.lists)
        
        board_list = BoardList(name=name, board_id=board_id, position=position)
        board.lists.append(board_list)
        board.lists.sort(key=lambda l: l.position)
        
        self._save_boards()
        return board_list
    
    def update_list(self, list_id: str, **kwargs) -> Optional[BoardList]:
        for board in self._boards.values():
            for board_list in board.lists:
                if board_list.id == list_id:
                    if "name" in kwargs:
                        board_list.name = kwargs["name"]
                    if "position" in kwargs:
                        board_list.position = kwargs["position"]
                    if "auto_archive" in kwargs:
                        board_list.auto_archive = kwargs["auto_archive"]
                    if "default_template" in kwargs:
                        board_list.default_template = kwargs["default_template"]
                    
                    self._save_boards()
                    return board_list
        return None
    
    def delete_list(self, list_id: str) -> bool:
        for board in self._boards.values():
            for i, board_list in enumerate(board.lists):
                if board_list.id == list_id:
                    # 归档所有卡片
                    board.archived_cards.extend(board_list.cards)
                    board.lists.pop(i)
                    self._save_boards()
                    return True
        return False
    
    # === Card API ===
    def get_card(self, card_id: str) -> Optional[Card]:
        for board in self._boards.values():
            for board_list in board.lists:
                for card in board_list.cards:
                    if card.id == card_id:
                        return card
            for card in board.archived_cards:
                if card.id == card_id:
                    return card
        return None
    
    def create_card(self, list_id: str, title: str, **kwargs) -> Optional[Card]:
        for board in self._boards.values():
            for board_list in board.lists:
                if board_list.id == list_id:
                    position = kwargs.get("position", len(board_list.cards))
                    card = Card(
                        title=title,
                        list_id=list_id,
                        position=position,
                        description=kwargs.get("description", ""),
                        due_date=kwargs.get("due_date"),
                        reminder_minutes=kwargs.get("reminder_minutes", 15),
                        labels=kwargs.get("labels", [])
                    )
                    
                    # 应用列表默认模板
                    if board_list.default_template:
                        for template_item in board_list.default_template:
                            card.checklist.append(ChecklistItem(text=template_item))
                    
                    board_list.cards.append(card)
                    self._save_boards()
                    return card
        return None

    # 在 JsonStorage 类中，替换 update_card 方法
    def update_card(self, card_id: str, **kwargs) -> Optional[Card]:
        card = self.get_card(card_id)
        if not card:
            return None

        # 处理 list_id 变更（移动卡片）
        new_list_id = kwargs.get("list_id")
        if new_list_id and new_list_id != card.list_id:
            # 从原列表中移除
            for board in self._boards.values():
                for lst in board.lists:
                    if lst.id == card.list_id:
                        lst.cards = [c for c in lst.cards if c.id != card_id]
                        break
            # 添加到新列表
            for board in self._boards.values():
                for lst in board.lists:
                    if lst.id == new_list_id:
                        card.list_id = new_list_id
                        # 默认放在末尾
                        card.position = len(lst.cards)
                        lst.cards.append(card)
                        break
            # 更新其他属性
            for key, value in kwargs.items():
                if key == "title":
                    card.title = value
                elif key == "description":
                    card.description = value
                elif key == "position":
                    card.position = value
                elif key == "due_date":
                    card.due_date = value
                elif key == "reminder_minutes":
                    card.reminder_minutes = value
                elif key == "labels":
                    card.labels = value
                elif key == "is_pinned":
                    card.is_pinned = value
                elif key == "checklist":
                    card.checklist = [ChecklistItem(**item) for item in value]
                elif key == "attachments":
                    card.attachments = value
            card.updated_at = datetime.now()
            self._save_boards()
            return card

        # 普通更新（不改变列表）
        for key, value in kwargs.items():
            if key == "title":
                card.title = value
            elif key == "description":
                card.description = value
            elif key == "position":
                card.position = value
            elif key == "due_date":
                card.due_date = value
            elif key == "reminder_minutes":
                card.reminder_minutes = value
            elif key == "labels":
                card.labels = value
            elif key == "is_pinned":
                card.is_pinned = value
            elif key == "checklist":
                card.checklist = [ChecklistItem(**item) for item in value]
            elif key == "attachments":
                card.attachments = value
        card.updated_at = datetime.now()
        self._save_boards()
        return card
    
    def _move_card_to_list(self, card: Card, new_list_id: str):
        # 从旧列表移除
        for board in self._boards.values():
            for board_list in board.lists:
                if board_list.id == card.list_id:
                    board_list.cards = [c for c in board_list.cards if c.id != card.id]
                if board_list.id == new_list_id:
                    card.list_id = new_list_id
                    card.position = len(board_list.cards)
                    board_list.cards.append(card)
    
    def delete_card(self, card_id: str, permanent: bool = False) -> bool:
        for board in self._boards.values():
            # 在列表中查找
            for board_list in board.lists:
                for i, card in enumerate(board_list.cards):
                    if card.id == card_id:
                        if permanent:
                            board_list.cards.pop(i)
                        else:
                            card.is_archived = True
                            board.archived_cards.append(card)
                            board_list.cards.pop(i)
                        self._save_boards()
                        return True
            
            # 在归档中查找
            for i, card in enumerate(board.archived_cards):
                if card.id == card_id:
                    if permanent:
                        board.archived_cards.pop(i)
                        self._save_boards()
                        return True
                    else:
                        # 恢复卡片
                        card.is_archived = False
                        for board_list in board.lists:
                            if board_list.id == card.list_id:
                                board_list.cards.append(card)
                                board.archived_cards.pop(i)
                                self._save_boards()
                                return True
        return False
    
    def archive_card(self, card_id: str) -> bool:
        return self.delete_card(card_id, permanent=False)
    
    def restore_card(self, card_id: str) -> bool:
        return self.delete_card(card_id, permanent=False)
    
    # === Label API ===
    def create_label(self, board_id: str, name: str, color: str) -> Optional[Label]:
        board = self._boards.get(board_id)
        if not board:
            return None
        
        label = Label(name=name, color=color)
        board.labels.append(label)
        self._save_boards()
        return label
    
    def update_label(self, label_id: str, **kwargs) -> Optional[Label]:
        for board in self._boards.values():
            for label in board.labels:
                if label.id == label_id:
                    if "name" in kwargs:
                        label.name = kwargs["name"]
                    if "color" in kwargs:
                        label.color = kwargs["color"]
                    self._save_boards()
                    return label
        return None
    
    def delete_label(self, label_id: str) -> bool:
        for board in self._boards.values():
            for i, label in enumerate(board.labels):
                if label.id == label_id:
                    # 从所有卡片中移除该标签
                    for board_list in board.lists:
                        for card in board_list.cards:
                            if label_id in card.labels:
                                card.labels.remove(label_id)
                    board.labels.pop(i)
                    self._save_boards()
                    return True
        return False
    
    # === Pomodoro API ===
    def get_pomodoro_settings(self) -> PomodoroSettings:
        return self._pomodoro_settings
    
    def update_pomodoro_settings(self, **kwargs) -> PomodoroSettings:
        if "focus_duration" in kwargs:
            self._pomodoro_settings.focus_duration = kwargs["focus_duration"]
        if "short_break_duration" in kwargs:
            self._pomodoro_settings.short_break_duration = kwargs["short_break_duration"]
        if "long_break_duration" in kwargs:
            self._pomodoro_settings.long_break_duration = kwargs["long_break_duration"]
        if "long_break_interval" in kwargs:
            self._pomodoro_settings.long_break_interval = kwargs["long_break_interval"]
        if "enable_sound" in kwargs:
            self._pomodoro_settings.enable_sound = kwargs["enable_sound"]
        if "sound_type" in kwargs:
            self._pomodoro_settings.sound_type = kwargs["sound_type"]
        if "enable_notification" in kwargs:
            self._pomodoro_settings.enable_notification = kwargs["enable_notification"]
        
        self._save_settings()
        return self._pomodoro_settings
    
    def add_pomodoro_session(self, session: PomodoroSession) -> PomodoroSession:
        self._sessions.append(session)
        
        # 更新每日统计
        date_str = session.created_at.date().isoformat()
        if date_str not in self._daily_stats:
            self._daily_stats[date_str] = DailyStats(stats_date=session.created_at.date())
        
        stats = self._daily_stats[date_str]
        stats.total_sessions += 1
        if session.completed:
            stats.completed_sessions += 1
            stats.total_focus_minutes += session.duration_minutes
            
            # 更新卡片统计
            if session.card_id:
                card = self.get_card(session.card_id)
                if card:
                    card.pomodoro_count += 1
                    card.total_focus_minutes += session.duration_minutes
                    
                if session.card_id not in stats.sessions_by_card:
                    stats.sessions_by_card[session.card_id] = 0
                stats.sessions_by_card[session.card_id] += 1
        
        self._save_pomodoro()
        self._save_boards()
        return session
    
    def get_today_stats(self) -> DailyStats:
        from datetime import date
        date_str = date.today().isoformat()
        return self._daily_stats.get(date_str, DailyStats())
    
    def get_stats_by_date_range(self, start_date: str, end_date: str) -> List[DailyStats]:
        from datetime import datetime as dt
        results = []
        start = dt.strptime(start_date, "%Y-%m-%d").date()
        end = dt.strptime(end_date, "%Y-%m-%d").date()
        
        current = start
        while current <= end:
            date_str = current.isoformat()
            stats = self._daily_stats.get(date_str, DailyStats(stats_date=current))
            results.append(stats)
            current = date.fromordinal(current.toordinal() + 1)
        
        return results

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import uuid

@dataclass
class Label:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    color: str = "#3498db"  # 默认蓝色

@dataclass
class ChecklistItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    completed: bool = False

@dataclass
class Card:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    list_id: str = ""
    position: int = 0
    due_date: Optional[datetime] = None
    reminder_minutes: int = 15  # 提前提醒分钟数
    labels: List[str] = field(default_factory=list)  # Label IDs
    checklist: List[ChecklistItem] = field(default_factory=list)
    attachments: List[Dict] = field(default_factory=list)
    is_pinned: bool = False
    is_archived: bool = False
    pomodoro_count: int = 0  # 累计番茄数
    total_focus_minutes: int = 0  # 累计专注分钟数
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def checklist_progress(self) -> float:
        if not self.checklist:
            return 0.0
        completed = sum(1 for item in self.checklist if item.completed)
        return completed / len(self.checklist)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "list_id": self.list_id,
            "position": self.position,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "reminder_minutes": self.reminder_minutes,
            "labels": self.labels,
            "checklist": [
                {"id": item.id, "text": item.text, "completed": item.completed}
                for item in self.checklist
            ],
            "attachments": self.attachments,
            "is_pinned": self.is_pinned,
            "is_archived": self.is_archived,
            "pomodoro_count": self.pomodoro_count,
            "total_focus_minutes": self.total_focus_minutes,
            "checklist_progress": self.checklist_progress,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

@dataclass
class BoardList:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    board_id: str = ""
    position: int = 0
    default_template: List[str] = field(default_factory=list)  # 默认检查清单模板
    auto_archive: str = "never"  # never, immediate, after_24h
    cards: List[Card] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "board_id": self.board_id,
            "position": self.position,
            "default_template": self.default_template,
            "auto_archive": self.auto_archive,
            "cards": [card.to_dict() for card in sorted(self.cards, key=lambda c: (not c.is_pinned, c.position))]
        }

@dataclass
class Board:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "新看板"
    background_color: str = "#f5f5f5"
    lists: List[BoardList] = field(default_factory=list)
    labels: List[Label] = field(default_factory=list)
    archived_cards: List[Card] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "background_color": self.background_color,
            "lists": [list_obj.to_dict() for list_obj in sorted(self.lists, key=lambda l: l.position)],
            "labels": [{"id": l.id, "name": l.name, "color": l.color} for l in self.labels],
            "archived_count": len(self.archived_cards),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict
from enum import Enum
import uuid

class TimerState(Enum):
    IDLE = "idle"
    FOCUSING = "focusing"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    PAUSED = "paused"

@dataclass
class PomodoroSettings:
    focus_duration: int = 25  # 分钟
    short_break_duration: int = 5  # 分钟
    long_break_duration: int = 15  # 分钟
    long_break_interval: int = 4  # 每几个番茄钟一次长休息
    enable_sound: bool = True
    sound_type: str = "bell"  # bell, tick, digital
    enable_notification: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "focus_duration": self.focus_duration,
            "short_break_duration": self.short_break_duration,
            "long_break_duration": self.long_break_duration,
            "long_break_interval": self.long_break_interval,
            "enable_sound": self.enable_sound,
            "sound_type": self.sound_type,
            "enable_notification": self.enable_notification
        }

@dataclass
class PomodoroSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    card_id: Optional[str] = None  # 绑定的任务卡片
    card_title: str = ""  # 任务标题（用于显示）
    state: TimerState = TimerState.IDLE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: int = 25
    completed: bool = False
    interrupted: bool = False
    interruption_reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def actual_duration_minutes(self) -> int:
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "card_id": self.card_id,
            "card_title": self.card_title,
            "state": self.state.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "actual_duration_minutes": self.actual_duration_minutes,
            "completed": self.completed,
            "interrupted": self.interrupted,
            "interruption_reason": self.interruption_reason,
            "created_at": self.created_at.isoformat()
        }

@dataclass
class DailyStats:
    stats_date: date = field(default_factory=date.today)
    total_sessions: int = 0
    completed_sessions: int = 0
    total_focus_minutes: int = 0
    sessions_by_card: Dict[str, int] = field(default_factory=dict)  # card_id -> count
    
    def to_dict(self) -> Dict:
        return {
            "date": self.stats_date.isoformat(),
            "total_sessions": self.total_sessions,
            "completed_sessions": self.completed_sessions,
            "total_focus_minutes": self.total_focus_minutes,
            "sessions_by_card": self.sessions_by_card
        }

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from storage.json_storage import JsonStorage
from models.pomodoro import PomodoroSession, PomodoroSettings, TimerState, DailyStats
from typing import List, Dict

class PomodoroService:
    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self._current_session: Optional[PomodoroSession] = None
        self._completed_today = 0  # 今日已完成番茄数

    # === Settings ===
    def get_settings(self) -> Dict:
        return self.storage.get_pomodoro_settings().to_dict()

    def update_settings(self, **kwargs) -> Dict:
        settings = self.storage.update_pomodoro_settings(**kwargs)
        return settings.to_dict()

    # === Session Management ===
    def start_session(self, card_id: str = None, card_title: str = "") -> Dict:
        settings = self.storage.get_pomodoro_settings()

        # 检查是否需要长休息
        if self._completed_today > 0 and self._completed_today % settings.long_break_interval == 0:
            duration = settings.long_break_duration
            state = TimerState.LONG_BREAK
        else:
            duration = settings.focus_duration
            state = TimerState.FOCUSING

        session = PomodoroSession(
            card_id=card_id,
            card_title=card_title,
            state=state,
            duration_minutes=duration
        )
        session.start_time = datetime.now()

        self._current_session = session

        return {
            "session_id": session.id,
            "card_id": card_id,
            "card_title": card_title,
            "state": state.value,
            "duration_minutes": duration,
            "start_time": session.start_time.isoformat()
        }

    def pause_session(self) -> Optional[Dict]:
        if not self._current_session:
            return None

        self._current_session.state = TimerState.PAUSED

        return {
            "session_id": self._current_session.id,
            "state": TimerState.PAUSED.value,
            "elapsed_minutes": self._get_elapsed_minutes()
        }

    def resume_session(self) -> Optional[Dict]:
        if not self._current_session:
            return None

        # 恢复之前的计时状态
        if self._current_session.state == TimerState.PAUSED:
            # 计算暂停期间的时间并调整开始时间
            # 简化处理：直接继续
            settings = self.storage.get_pomodoro_settings()

            if self._completed_today > 0 and self._completed_today % settings.long_break_interval == 0:
                self._current_session.state = TimerState.LONG_BREAK
            else:
                self._current_session.state = TimerState.FOCUSING

        return {
            "session_id": self._current_session.id,
            "state": self._current_session.state.value,
            "duration_minutes": self._current_session.duration_minutes,
            "elapsed_minutes": self._get_elapsed_minutes()
        }

    def stop_session(self, completed: bool = False, interrupted: bool = False, reason: str = "") -> Optional[Dict]:
        if not self._current_session:
            return None

        session = self._current_session
        session.end_time = datetime.now()
        session.completed = completed
        session.interrupted = interrupted
        session.interruption_reason = reason
        session.state = TimerState.IDLE

        # 保存会话
        self.storage.add_pomodoro_session(session)

        if completed:
            self._completed_today += 1

        result = session.to_dict()
        self._current_session = None

        return result

    def get_current_session(self) -> Optional[Dict]:
        if not self._current_session:
            return None

        return {
            "session_id": self._current_session.id,
            "card_id": self._current_session.card_id,
            "card_title": self._current_session.card_title,
            "state": self._current_session.state.value,
            "duration_minutes": self._current_session.duration_minutes,
            "elapsed_minutes": self._get_elapsed_minutes(),
            "remaining_seconds": self._get_remaining_seconds(),
            "start_time": self._current_session.start_time.isoformat() if self._current_session.start_time else None
        }

    def _get_elapsed_minutes(self) -> int:
        if not self._current_session or not self._current_session.start_time:
            return 0

        elapsed = datetime.now() - self._current_session.start_time
        return int(elapsed.total_seconds() / 60)

    def _get_remaining_seconds(self) -> int:
        if not self._current_session:
            return 0

        elapsed_seconds = self._get_elapsed_minutes() * 60
        total_seconds = self._current_session.duration_minutes * 60
        remaining = total_seconds - elapsed_seconds

        return max(0, remaining)

    def start_break(self, break_type: str = "short") -> Dict:
        settings = self.storage.get_pomodoro_settings()

        if break_type == "long":
            duration = settings.long_break_duration
            state = TimerState.LONG_BREAK
        else:
            duration = settings.short_break_duration
            state = TimerState.SHORT_BREAK

        session = PomodoroSession(
            state=state,
            duration_minutes=duration
        )
        session.start_time = datetime.now()

        self._current_session = session

        return {
            "session_id": session.id,
            "state": state.value,
            "duration_minutes": duration,
            "start_time": session.start_time.isoformat()
        }

    # === Statistics ===
    def get_daily_stats(self, for_date: date) -> Dict:
        date_str = for_date.isoformat()
        stats = self.storage._daily_stats.get(
            date_str, DailyStats(stats_date=for_date)
        )
        return {
            "date": stats.stats_date.isoformat(),
            "total_sessions": stats.total_sessions,
            "completed_sessions": stats.completed_sessions,
            "total_focus_minutes": stats.total_focus_minutes,
            "completion_rate": (
                    stats.completed_sessions / stats.total_sessions * 100
            )
            if stats.total_sessions > 0
            else 0,
        }

    def get_today_stats(self) -> Dict:
        return self.get_daily_stats(date.today())

    def get_stats_by_range(self, start_date: str, end_date: str) -> List[Dict]:
        stats_list = self.storage.get_stats_by_date_range(start_date, end_date)
        return [stats.to_dict() for stats in stats_list]

    def get_card_stats(self, card_id: str) -> Dict:
        sessions = []
        total_minutes = 0
        completed_count = 0

        # 这里需要从存储中查询特定卡片的会话
        # 简化实现：返回基于卡片的统计
        card = self.storage.get_card(card_id)
        if card:
            return {
                "card_id": card_id,
                "card_title": card.title,
                "total_pomodoros": card.pomodoro_count,
                "total_focus_minutes": card.total_focus_minutes
            }

        return {
            "card_id": card_id,
            "total_pomodoros": 0,
            "total_focus_minutes": 0
        }

    def get_weekly_report(self) -> Dict:
        from datetime import date, timedelta

        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        dates = []
        sessions = []
        minutes = []

        for i in range(7):
            current_date = start_of_week + timedelta(days=i)
            date_str = current_date.isoformat()
            stats = self.storage._daily_stats.get(date_str, DailyStats(stats_date=current_date))

            dates.append(date_str)
            sessions.append(stats.completed_sessions)
            minutes.append(stats.total_focus_minutes)

        return {
            "week_start": start_of_week.isoformat(),
            "week_end": (start_of_week + timedelta(days=6)).isoformat(),
            "daily_stats": {
                "dates": dates,
                "completed_sessions": sessions,
                "focus_minutes": minutes
            },
            "total_sessions": sum(sessions),
            "total_minutes": sum(minutes)
        }

    # === Timer State Check ===
    def check_timer_completion(self) -> Optional[Dict]:
        if not self._current_session:
            return None

        remaining = self._get_remaining_seconds()

        if remaining <= 0:
            # 计时完成
            session = self._current_session
            session.end_time = datetime.now()

            if session.state in [TimerState.FOCUSING, TimerState.PAUSED]:
                session.completed = True
                self._completed_today += 1

            self.storage.add_pomodoro_session(session)

            result = {
                "completed": True,
                "session": session.to_dict(),
                "next_action": "break" if session.state == TimerState.FOCUSING else "focus"
            }

            self._current_session = None
            return result

        return {
            "completed": False,
            "remaining_seconds": remaining
        }

    def get_sessions_by_date(self, target_date: date) -> List[Dict]:
        date_str = target_date.isoformat()
        sessions = []
        for session in self.storage._sessions:
            if session.created_at.date().isoformat() == date_str:
                sessions.append(session.to_dict())
        return sessions

    def get_next_session_type(self):
        settings = self.storage.get_pomodoro_settings()
        # 注意：_completed_today 是本次应用启动后完成的番茄数，需要从 storage 中获取当日已完成数
        # 为简化，我们使用 _completed_today 成员变量，它在 stop_session(completed=True) 时递增
        # 因此这里直接使用 self._completed_today 即可
        if self._completed_today > 0 and self._completed_today % settings.long_break_interval == 0:
            return "long", settings.long_break_duration
        else:
            return "short", settings.short_break_duration

    def start_break(self, break_type="short"):
        settings = self.storage.get_pomodoro_settings()
        if break_type == "long":
            duration = settings.long_break_duration
            state = "long_break"
        else:
            duration = settings.short_break_duration
            state = "short_break"
        session = PomodoroSession(state=TimerState(state), duration_minutes=duration)
        session.start_time = datetime.now()
        self._current_session = session
        return {
            "session_id": session.id,
            "state": state,
            "duration_minutes": duration,
            "start_time": session.start_time.isoformat()
        }
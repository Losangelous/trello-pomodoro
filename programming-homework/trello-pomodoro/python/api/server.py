import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from storage import JsonStorage
from services import BoardService, PomodoroService

# 全局服务实例
storage: Optional[JsonStorage] = None
board_service: Optional[BoardService] = None
pomodoro_service: Optional[PomodoroService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global storage, board_service, pomodoro_service
    
    # 启动时初始化
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
    storage = JsonStorage(data_dir)
    board_service = BoardService(storage)
    pomodoro_service = PomodoroService(storage)
    
    print(f"✓ 数据目录: {data_dir}")
    print(f"✓ 服务已启动")
    
    yield
    
    # 关闭时清理
    print("✓ 服务已关闭")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Trello Pomodoro API",
        description="个人任务看板与番茄钟后端服务",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # 启用 CORS（允许 C++ 客户端访问）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # === Pydantic Models ===
    class BoardCreate(BaseModel):
        name: str
        background_color: str = "#f5f5f5"
    
    class BoardUpdate(BaseModel):
        name: Optional[str] = None
        background_color: Optional[str] = None
    
    class ListCreate(BaseModel):
        name: str
        position: Optional[int] = None
    
    class ListUpdate(BaseModel):
        name: Optional[str] = None
        position: Optional[int] = None
        auto_archive: Optional[str] = None
    
    class CardCreate(BaseModel):
        title: str
        description: str = ""
        due_date: Optional[str] = None
        reminder_minutes: int = 15
        labels: List[str] = Field(default_factory=list)
    
    class CardUpdate(BaseModel):
        title: Optional[str] = None
        description: Optional[str] = None
        due_date: Optional[str] = None
        reminder_minutes: Optional[int] = None
        labels: Optional[List[str]] = None
        is_pinned: Optional[bool] = None
        checklist: Optional[List[dict]] = None
    
    class CardMove(BaseModel):
        target_list_id: str
        target_position: Optional[int] = None
    
    class ChecklistItemCreate(BaseModel):
        text: str
    
    class LabelCreate(BaseModel):
        name: str
        color: str
    
    class LabelUpdate(BaseModel):
        name: Optional[str] = None
        color: Optional[str] = None
    
    class PomodoroStart(BaseModel):
        card_id: Optional[str] = None
        card_title: str = ""
    
    class PomodoroStop(BaseModel):
        completed: bool = False
        interrupted: bool = False
        reason: str = ""
    
    class PomodoroSettingsUpdate(BaseModel):
        focus_duration: Optional[int] = None
        short_break_duration: Optional[int] = None
        long_break_duration: Optional[int] = None
        long_break_interval: Optional[int] = None
        enable_sound: Optional[bool] = None
        sound_type: Optional[str] = None
        enable_notification: Optional[bool] = None
    
    # === Board Routes ===
    @app.get("/api/boards")
    async def get_boards():
        return {"boards": board_service.get_all_boards()}
    
    @app.get("/api/boards/{board_id}")
    async def get_board(board_id: str):
        board = board_service.get_board(board_id)
        if not board:
            raise HTTPException(status_code=404, detail="看板不存在")
        return board
    
    @app.post("/api/boards")
    async def create_board(data: BoardCreate):
        board = board_service.create_board(data.name, data.background_color)
        return board
    
    @app.patch("/api/boards/{board_id}")
    async def update_board(board_id: str, data: BoardUpdate):
        board = board_service.update_board(board_id, data.name, data.background_color)
        if not board:
            raise HTTPException(status_code=404, detail="看板不存在")
        return board
    
    @app.delete("/api/boards/{board_id}")
    async def delete_board(board_id: str):
        if board_service.delete_board(board_id):
            return {"message": "删除成功"}
        raise HTTPException(status_code=404, detail="看板不存在")
    
    # === List Routes ===
    @app.post("/api/boards/{board_id}/lists")
    async def create_list(board_id: str, data: ListCreate):
        board_list = board_service.create_list(board_id, data.name, data.position)
        if not board_list:
            raise HTTPException(status_code=404, detail="看板不存在")
        return board_list
    
    @app.patch("/api/lists/{list_id}")
    async def update_list(list_id: str, data: ListUpdate):
        kwargs = {k: v for k, v in data.dict().items() if v is not None}
        board_list = board_service.update_list(list_id, **kwargs)
        if not board_list:
            raise HTTPException(status_code=404, detail="列表不存在")
        return board_list
    
    @app.delete("/api/lists/{list_id}")
    async def delete_list(list_id: str):
        if board_service.delete_list(list_id):
            return {"message": "删除成功"}
        raise HTTPException(status_code=404, detail="列表不存在")
    
    @app.post("/api/boards/{board_id}/lists/reorder")
    async def reorder_lists(board_id: str, list_ids: List[str]):
        if board_service.reorder_lists(board_id, list_ids):
            return {"message": "排序成功"}
        raise HTTPException(status_code=404, detail="看板不存在")
    
    # === Card Routes ===
    @app.get("/api/cards/{card_id}")
    async def get_card(card_id: str):
        card = board_service.get_card(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return card
    
    @app.post("/api/lists/{list_id}/cards")
    async def create_card(list_id: str, data: CardCreate):
        kwargs = {
            "description": data.description,
            "reminder_minutes": data.reminder_minutes,
            "labels": data.labels
        }
        if data.due_date:
            kwargs["due_date"] = datetime.fromisoformat(data.due_date.replace('Z', '+00:00'))
        
        card = board_service.create_card(list_id, data.title, **kwargs)
        if not card:
            raise HTTPException(status_code=404, detail="列表不存在")
        return card
    
    @app.patch("/api/cards/{card_id}")
    async def update_card(card_id: str, data: CardUpdate):
        kwargs = {k: v for k, v in data.dict().items() if v is not None}
        if "due_date" in kwargs and kwargs["due_date"]:
            kwargs["due_date"] = datetime.fromisoformat(kwargs["due_date"].replace('Z', '+00:00'))
        
        card = board_service.update_card(card_id, **kwargs)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return card
    
    @app.post("/api/cards/{card_id}/move")
    async def move_card(card_id: str, data: CardMove):
        card = board_service.move_card(card_id, data.target_list_id, data.target_position)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return card
    
    @app.delete("/api/cards/{card_id}")
    async def delete_card(card_id: str, permanent: bool = False):
        if board_service.delete_card(card_id, permanent):
            return {"message": "删除成功"}
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    @app.post("/api/cards/{card_id}/archive")
    async def archive_card(card_id: str):
        if board_service.archive_card(card_id):
            return {"message": "归档成功"}
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    @app.post("/api/cards/{card_id}/restore")
    async def restore_card(card_id: str):
        if board_service.restore_card(card_id):
            return {"message": "恢复成功"}
        raise HTTPException(status_code=404, detail="卡片不存在")
    
    @app.post("/api/cards/{card_id}/pin")
    async def pin_card(card_id: str):
        card = board_service.pin_card(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return card
    
    @app.post("/api/cards/{card_id}/unpin")
    async def unpin_card(card_id: str):
        card = board_service.unpin_card(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return card
    
    @app.post("/api/lists/{list_id}/cards/reorder")
    async def reorder_cards(list_id: str, card_ids: List[str]):
        if board_service.reorder_cards(list_id, card_ids):
            return {"message": "排序成功"}
        raise HTTPException(status_code=404, detail="列表不存在")
    
    # === Checklist Routes ===
    @app.post("/api/cards/{card_id}/checklist")
    async def add_checklist_item(card_id: str, data: ChecklistItemCreate):
        card = board_service.add_checklist_item(card_id, data.text)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return card
    
    @app.patch("/api/cards/{card_id}/checklist/{item_id}")
    async def toggle_checklist_item(card_id: str, item_id: str):
        card = board_service.toggle_checklist_item(card_id, item_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片或清单项不存在")
        return card
    
    @app.delete("/api/cards/{card_id}/checklist/{item_id}")
    async def remove_checklist_item(card_id: str, item_id: str):
        card = board_service.remove_checklist_item(card_id, item_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return card
    
    # === Label Routes ===
    @app.post("/api/boards/{board_id}/labels")
    async def create_label(board_id: str, data: LabelCreate):
        label = board_service.create_label(board_id, data.name, data.color)
        if not label:
            raise HTTPException(status_code=404, detail="看板不存在")
        return label
    
    @app.patch("/api/labels/{label_id}")
    async def update_label(label_id: str, data: LabelUpdate):
        label = board_service.update_label(label_id, data.name, data.color)
        if not label:
            raise HTTPException(status_code=404, detail="标签不存在")
        return label
    
    @app.delete("/api/labels/{label_id}")
    async def delete_label(label_id: str):
        if board_service.delete_label(label_id):
            return {"message": "删除成功"}
        raise HTTPException(status_code=404, detail="标签不存在")
    
    @app.post("/api/cards/{card_id}/labels/{label_id}")
    async def add_label_to_card(card_id: str, label_id: str):
        card = board_service.add_label_to_card(card_id, label_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片或标签不存在")
        return card
    
    @app.delete("/api/cards/{card_id}/labels/{label_id}")
    async def remove_label_from_card(card_id: str, label_id: str):
        card = board_service.remove_label_from_card(card_id, label_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片或标签不存在")
        return card
    
    # === Search Routes ===
    @app.get("/api/search")
    async def search(query: str, board_id: Optional[str] = None):
        results = board_service.search(query, board_id)
        return {"results": results, "count": len(results)}
    
    # === Archive Routes ===
    @app.get("/api/boards/{board_id}/archived")
    async def get_archived_cards(board_id: str):
        return {"cards": board_service.get_archived_cards(board_id)}
    
    @app.delete("/api/boards/{board_id}/archived")
    async def clear_archived_cards(board_id: str):
        if board_service.clear_archived_cards(board_id):
            return {"message": "清空成功"}
        raise HTTPException(status_code=404, detail="看板不存在")
    
    # === Due Date Routes ===
    @app.get("/api/cards/overdue")
    async def get_overdue_cards():
        return {"cards": board_service.get_overdue_cards()}
    
    @app.get("/api/cards/today-due")
    async def get_today_due_cards():
        return {"cards": board_service.get_today_due_cards()}
    
    # === Pomodoro Routes ===
    @app.get("/api/pomodoro/settings")
    async def get_pomodoro_settings():
        return pomodoro_service.get_settings()
    
    @app.patch("/api/pomodoro/settings")
    async def update_pomodoro_settings(data: PomodoroSettingsUpdate):
        kwargs = {k: v for k, v in data.dict().items() if v is not None}
        return pomodoro_service.update_settings(**kwargs)
    
    @app.post("/api/pomodoro/start")
    async def start_pomodoro(data: PomodoroStart):
        return pomodoro_service.start_session(data.card_id, data.card_title)
    
    @app.post("/api/pomodoro/pause")
    async def pause_pomodoro():
        result = pomodoro_service.pause_session()
        if not result:
            raise HTTPException(status_code=400, detail="没有正在进行的专注")
        return result
    
    @app.post("/api/pomodoro/resume")
    async def resume_pomodoro():
        result = pomodoro_service.resume_session()
        if not result:
            raise HTTPException(status_code=400, detail="没有暂停的专注")
        return result
    
    @app.post("/api/pomodoro/stop")
    async def stop_pomodoro(data: PomodoroStop):
        result = pomodoro_service.stop_session(data.completed, data.interrupted, data.reason)
        if not result:
            raise HTTPException(status_code=400, detail="没有正在进行的专注")
        return result
    
    @app.get("/api/pomodoro/current")
    async def get_current_session():
        result = pomodoro_service.get_current_session()
        if not result:
            return {"session": None}
        return {"session": result}
    
    @app.get("/api/pomodoro/check")
    async def check_timer():
        result = pomodoro_service.check_timer_completion()
        return result or {"completed": False}
    
    @app.get("/api/pomodoro/stats/today")
    async def get_today_stats():
        return pomodoro_service.get_today_stats()
    
    @app.get("/api/pomodoro/stats/range")
    async def get_stats_range(start_date: str, end_date: str):
        return {"stats": pomodoro_service.get_stats_by_range(start_date, end_date)}
    
    @app.get("/api/pomodoro/stats/card/{card_id}")
    async def get_card_pomodoro_stats(card_id: str):
        return pomodoro_service.get_card_stats(card_id)
    
    @app.get("/api/pomodoro/stats/weekly")
    async def get_weekly_stats():
        return pomodoro_service.get_weekly_report()
    
    # === Health Check ===
    @app.get("/api/health")
    async def health_check():
        return {"status": "ok", "version": "1.0.0"}
    
    return app

if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")

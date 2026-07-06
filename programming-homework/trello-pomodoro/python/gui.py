#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flet as ft
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.json_storage import JsonStorage
from services.board_service import BoardService
from services.pomodoro_service import PomodoroService
from services.data_export import load_pomodoro_data,generate_report_from_pomodoro
from services.goal_setting import get_today_goal,set_today_goal,get_pomodoro
from views.board_view import BoardView
from views.pomodoro_view import PomodoroView
from views.dark_theme import DarkTheme

def _project_data_dir():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.normpath(os.path.join(root, "data"))

class TrelloPomodoroApp:
    def __init__(self):
        self.storage = JsonStorage(_project_data_dir())
        self.board_service = BoardService(self.storage)
        self.pomodoro_service = PomodoroService(self.storage)

    def export_report(self,page:ft.Page):
        try:
            data=load_pomodoro_data()
            success,result=generate_report_from_pomodoro(data,"reports")
            if success:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"报告已生成：{result}")))
            else:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"报告生成失败：{result}")))
        except Exception as e:
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"错误:{str(e)}")))

    def set_goal(self,page:ft.Page):
        goal_input=ft.TextField(label="目标专注时长（分钟）",value=str(get_today_goal()))
        
        def save_goal(e):
            try:
                minutes=int(goal_input.value)
                if minutes<=0:
                    raise ValueError
                set_today_goal(minutes)
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"今日目标已设置为{minutes}分钟")))
                dialog.open=False
                page.update()
            except ValueError:
                goal_input.error_text="请输入有效的正整数"
                page.update()
        dialog = ft.AlertDialog(
        title=ft.Text("设置今日目标"),
        content=goal_input,
        actions=[
            ft.TextButton("取消", on_click=lambda e: setattr(dialog, "open", False)),
            ft.TextButton("保存", on_click=save_goal),
        ],
        )
        page.open(dialog)

    def check_goal(self, page: ft.Page):
        goal = get_today_goal()
        today_focus = get_pomodoro()
    
        status = "目标已完成" if today_focus >= goal else "目标未完成"
    
        dialog = ft.AlertDialog(
            title=ft.Text("今日目标完成情况"),
            content=ft.Text(
                f"今日目标（默认值为25分钟）：{goal} 分钟\n"
                f"已完成时长：{today_focus} 分钟\n"
                f"{status}"
            ),
            actions=[
                ft.TextButton("关闭", on_click=lambda e: setattr(dialog, "open", False))
            ],
        )
        page.open(dialog)
    def main(self, page: ft.Page):
        page.title = "Trello Pomodoro"
        theme_manager=DarkTheme(page)
        #page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 1280
        page.window.height = 800
        page.window.resizable = True
        page.padding = 10

        try:
            boards = self.board_service.get_all_boards()
            if not boards:
                board = self.board_service.create_board("我的任务看板")
                board_id = board["id"]
                print("已创建默认看板")
            else:
                board_id = boards[0]["id"]
                print(f"使用已有看板: {board_id}")

            board_view = BoardView(board_id, self.board_service,
                                   on_card_updated=lambda: self.pomodoro_view.refresh_cards())
            page.board_view=board_view
            pomodoro_view = PomodoroView(self.pomodoro_service, self.board_service)
            self.pomodoro_view = pomodoro_view

            page.appbar=ft.AppBar(title=ft.Text("Trello Pomodoro"),center_title=False,actions=[theme_manager.get_button(),ft.IconButton(icon=ft.icons.SETTINGS,on_click=lambda e: self.set_goal(page)),ft.IconButton(icon=ft.icons.BAR_CHART,on_click=lambda e: self.check_goal(page)),ft.IconButton(icon=ft.icons.DOWNLOAD,on_click=lambda e: self.export_report(page))])

            tabs = ft.Tabs(
                selected_index=0,
                tabs=[
                    ft.Tab(text="📋 看板", content=board_view),
                    ft.Tab(text="🍅 番茄钟", content=pomodoro_view),
                ],
                expand=True
            )
            page.add(tabs)
            page.update()
            print("GUI 启动成功")
        except Exception as e:
            print("启动出错：", traceback.format_exc())
            page.add(ft.Text(f"启动失败: {e}", color=ft.Colors.RED))
            page.update()

def main():
    try:
        app = TrelloPomodoroApp()
        ft.app(target=app.main, view=ft.AppView.FLET_APP)
    except Exception as e:
        traceback.print_exc()
        input("按Enter退出...")

if __name__ == "__main__":
    main()
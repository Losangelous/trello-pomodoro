#本.py文件用于设置今日专注时长目标（注：新一天开始时目标自动重置为25分钟，默认值为25分钟）
import json
import os
from datetime import datetime

def get_today_goal():
    today=datetime.now().strftime("%Y-%m-%d")
    file_path="../data/daily_goal.json"
    
    if not os.path.exists(file_path):
        return 25
    
    with open(file_path,'r',encoding='utf-8') as f:
        datas=json.load(f)
        file_date=datas.get("date")
        file_goal=datas.get("goal_minutes")

        if file_date!=today:
            return 25
        return file_goal

def set_today_goal(minute):
    today=datetime.now().strftime("%Y-%m-%d")
    file_path="../data/daily_goal.json"

    data={
        "date":today,
        "goal_minutes":minute
    }
    os.makedirs(os.path.dirname(file_path),exist_ok=True)

    with open(file_path,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def get_pomodoro():
    today=datetime.now().strftime("%Y-%m-%d")
    file_path="../data/pomodoro.json"
    
    with open(file_path,'r',encoding='utf-8') as f:
        datas=json.load(f)

    daily_stats=datas.get("daily_stats",{})
    if today in daily_stats:
        return daily_stats[today].get("total_focus_minutes",0)
    return 0
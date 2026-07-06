#本.py文件用于操作番茄钟数据的导出和报告的生成
import json
import os
from datetime import datetime
from collections import defaultdict
#print("当前工作目录:", os.getcwd())
#print("data/pomodoro.json 是否存在:", os.path.exists("data/pomodoro.json"))
def load_pomodoro_data(file_path=None):
    if file_path is None:
        file_path="../data/pomodoro.json"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在:{file_path}")
    with open(file_path,'r',encoding='utf-8') as f:
        return json.load(f)

def generate_report_from_pomodoro(data,output_dir="."):
    try:
        sessions=data.get("sessions",[])
        
        total_focus_time=0
        total_pomodoro_count=0
        all_cards=set()
        daily_data={}

        for single_session in sessions:
            total_pomodoro_count=total_pomodoro_count+1
            current_time=single_session.get("actual_duration_minutes",0)
            total_focus_time=total_focus_time+current_time

            start_time=single_session.get("start_time")
            if not start_time:
                continue
            date=start_time.split("T")[0]
            if date not in daily_data:
                daily_data[date]={"专注时长":0,"番茄数":0,"卡片集合":set()}

            daily_data[date]["专注时长"]+=current_time
            daily_data[date]["番茄数"]+=1

            card_id=single_session.get("card_id","")
            if card_id and card_id!="无特定任务":
                all_cards.add(card_id)
                daily_data[date]["卡片集合"].add(card_id)

        report_line=[]
        #report_line.append("标题及生成时间")
        report_line.append("【总计统计】")
        report_line.append(f"总专注时长:{total_focus_time}分钟")
        report_line.append(f"总番茄数:{total_pomodoro_count}个")
        report_line.append(f"完成任务数:{len(all_cards)}个卡片")
        report_line.append("【按日统计】")

        for date1 in sorted(daily_data.keys()):
            d=daily_data[date1]
            report_line.append(f"{date1}")
            report_line.append(f" 专注时长：{d['专注时长']}分钟")
            report_line.append(f" 番茄数：{d['番茄数']}个")
            report_line.append(f" 完成任务数：{len(d['卡片集合'])}个卡片")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pomodoro_report_{timestamp}.txt"
        complete_path=os.path.join(output_dir,filename)
        os.makedirs(output_dir,exist_ok=True)
        with open(complete_path,"w",encoding="utf-8") as f:
            f.write("\n".join(report_line))

        return (True,complete_path)
    
    except Exception as e:
        return (False,str(e))
import tkinter as tk
import json
import glob
import time
import threading
import os
import ctypes
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys
import pytz

# ─────────────────────────────────────────────
# Windows API 상수
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x00000008
LWA_ALPHA = 0x2
LWA_COLORKEY = 0x1

SetWindowLong = ctypes.windll.user32.SetWindowLongW
GetWindowLong = ctypes.windll.user32.GetWindowLongW
SetLayeredWindowAttributes = ctypes.windll.user32.SetLayeredWindowAttributes
GetParent = ctypes.windll.user32.GetParent

# ─────────────────────────────────────────────
# 설정
if getattr(sys, 'frozen', False):  # pyinstaller로 패킹된 상태인지 확인
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

json_dir = base_dir
FILE_PATH = os.path.join(json_dir, "../page_content_*.json")

# FILE_PATH = "../page_content_*.json"
# FILE_PATH = "../test_content.json"
TRANSPARENT_COLOR = "black"
BIG_FONT = "Pretendard Semibold"
SMALL_FONT_0 = "Pretendard"
SMALL_FONT_1 = "나눔고딕코딩"
CONFIG_PATH = "config.json"
DEFAULT_CONFIG = {
    "x": 100,
    "y": 100,
    "font_size": 64,
    "opacity": 255,
    "locked": False,
    "details_visible": True
}
LUNCH_TIME = timedelta(hours=12)
DINNER_TIME = timedelta(hours=18)
ZERO_HOURS = timedelta(hours=0)
ONE_HOURS = timedelta(hours=1)
details_visible = True
# ─────────────────────────────────────────────
# 설정 불러오기 / 저장
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config():
    cfg = {
        "x": root.winfo_x(),
        "y": root.winfo_y(),
        "font_size": label_font_size,
        "opacity": label_opacity,
        "locked": locked,
        "details_visible": details_visible
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ─────────────────────────────────────────────
# 시간 문자열 파싱 ("3:46", "7H 36M" 등)
def parse_duration(s: str) -> timedelta:
    # "7H 36M" → timedelta
    h_match = re.search(r'(\d+)\s*[Hh]', s)
    m_match = re.search(r'(\d+)\s*[Mm]', s)
    h = int(h_match.group(1)) if h_match else 0
    m = int(m_match.group(1)) if m_match else 0
    return timedelta(hours=h, minutes=m)

def parse_colon_time(s: str) -> timedelta:
    # "06:54" → timedelta
    parts = s.strip().split(":")
    h, m = int(parts[0]), int(parts[1])
    return timedelta(hours=h, minutes=m)

def parse_korean_time(s: str) -> timedelta:
    # "06시 54분" → timedelta
    hour_match = re.search(r'(\d+)\s*시', s)
    minute_match = re.search(r'(\d+)\s*분', s)

    h = int(hour_match.group(1)) if hour_match else None
    m = int(minute_match.group(1)) if minute_match else None
    return timedelta(hours=h, minutes=m)

def split_timedelta(td: timedelta):
    total_minutes = int(td.total_seconds() // 60)
    return total_minutes // 60, total_minutes % 60

def eating_time(td: timedelta) -> timedelta:
    if (td >= LUNCH_TIME) and (td < LUNCH_TIME + ONE_HOURS):
        td = LUNCH_TIME + ONE_HOURS
    if (td >= DINNER_TIME) and (td < DINNER_TIME + ONE_HOURS):
        td = DINNER_TIME + ONE_HOURS
    return td


# ─────────────────────────────────────────────
# 상태 판단 + 정보 추출
def get_status_and_times():
    now_korea = datetime.now(pytz.timezone("Asia/Seoul"))
    weekday = now_korea.strftime("%A")  # 예: 'Monday', 'Tuesday'
    # today = now_korea.date().day
    yesterday = (now_korea.date() - timedelta(days=1)).day
    if (weekday == "Sunday"):
        return "", "", "", False

    latest = sorted(glob.glob(FILE_PATH))[-1]
    with open(latest, 'r', encoding='utf-8') as f:
        data = json.load(f)
    now = datetime.now()
    current_time = timedelta(hours=now.hour, minutes=now.minute)
    current_time = eating_time(current_time)

    content = data.get("content", "")
    contents = content.split("\n")

    remain_time     = None # 전날까지 채우고 남은 시간
    today_time      = None # 오늘 채운 시간
    start_time      = None # 오늘 출근 시간
    finish_time     = None # 오늘 퇴근 시간
    real_time       = None # 전날 채우고 남은 시간 - 오늘 채운 시간
    end_time        = None # 오늘 출근 시간 + 남은 채워야하는 시간
    prev_work       = False # 전날 출근함?

    status = "출근"
    label_1 = ""
    label_2 = ""
    overlay = True

    day_start = 0
    day_end = 0
    for idx, item in enumerate(contents):
        if "금주 잔여 복무시간" in item:
            remain_time = parse_duration(contents[idx+1])
        elif "출근시간" in item:
            if "예상 누적"  in contents[idx+1]:
                start_time = parse_colon_time(contents[idx+2])
                start_time = eating_time(start_time)
                today_time = current_time - start_time # parse_colon_time(contents[idx+1].split(" ")[-1])
                if (start_time <= LUNCH_TIME) and (current_time >= LUNCH_TIME + ONE_HOURS):
                    today_time = today_time - ONE_HOURS
                if (start_time <= DINNER_TIME) and (current_time >= DINNER_TIME + ONE_HOURS):
                    today_time = today_time - ONE_HOURS

        elif "퇴근시간" in item:
            if not "스케줄" in contents[idx+1]:
                finish_time = parse_colon_time(contents[idx+1])
        elif "월\t화\t수\t목\t금" in item:
            day_start = idx
        elif "상신 목록" in item:
            day_end = idx

    for idx in range(day_start, day_end):
        item = contents[idx]
        if (f"{yesterday:02d}" == item):
            if (len(contents[idx+2]) == 2):
                prev_work = False
            else:
                prev_work = True

    if today_time is None:
        real_time = remain_time
    else:
        if (remain_time < today_time):
            real_time = ZERO_HOURS
        else:
            real_time = remain_time - today_time
        end_time = start_time + remain_time

        if (end_time >= LUNCH_TIME) and (start_time < LUNCH_TIME):
            end_time += ONE_HOURS
        if (end_time >= DINNER_TIME) and (start_time < DINNER_TIME):
            end_time += ONE_HOURS

    if finish_time is not None: # 퇴근함
        finish_h, finish_m = split_timedelta(finish_time)
        label_2 = f"{finish_h:02d}:{finish_m:02d}"
    # 남은 시간이 12시간 이상이거나 / 다 채울 수 있는 퇴근 시간이 자정을 넘기거나 / 아직 출근을 안함
    elif (remain_time > timedelta(hours=12)) or (end_time > timedelta(hours=24)) or (start_time is None):
        label_2 = ""
    else:
        end_h, end_m = split_timedelta(end_time)
        label_2 = f"{end_h:02d}:{end_m:02d}"
    
    if (start_time is not None) and (finish_time is None): # 출근
        status = "출근"
        real_h, real_m = split_timedelta(real_time)
        label_1 = f"{real_h:02d}:{real_m:02d}"
    elif (start_time is not None) and (finish_time is not None): # 자정 넘기기전에 퇴근한 경우
        status = "퇴근"
        remain_h, remain_m = split_timedelta(remain_time)
        label_1 = f"{remain_h:02d}:{remain_m:02d}"
    elif (start_time is None) and (finish_time is None): # 자정을 넘겼거나 아직 출근 안함
        if (weekday != "Monday") and (prev_work == False): # 월요일도 아닌데 전날 아무 기록이 없음 > 자정을 넘긴 출근 상태
            status = "출근"
            label_1 = ""
            label_2 = ""
        else:
            status = "퇴근"
    
    if (real_time == ZERO_HOURS) and (status == "퇴근"):
        overlay = False

    return status, label_1, label_2, overlay

# ─────────────────────────────────────────────
# UI 갱신
def update_labels():
    while True:
        try:
            status, remaining, target_time, overlay = get_status_and_times()
            if overlay:
                label_status.config(text=status)
                label_info_1.config(text=remaining)
                label_info_2.config(text=target_time)
                label_info_01.config(text="잔여")
                label_info_02.config(text="퇴근")
            else:
                label_status.config(text="")
                label_info_1.config(text="")
                label_info_2.config(text="")
                label_info_01.config(text="")
                label_info_02.config(text="")
            
            files = glob.glob(FILE_PATH)
            for file in files:
                try:
                    os.remove(file)
                except Exception as e:
                    time.sleep(0.1)
        except:
            time.sleep(0.1)
        time.sleep(60)

# ─────────────────────────────────────────────
# 투명도 및 클릭 패스스루
def set_opacity(alpha):
    hwnd = GetParent(root.winfo_id())
    style = GetWindowLong(hwnd, GWL_EXSTYLE)
    SetWindowLong(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
    SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA | LWA_COLORKEY)

def set_click_through(enable):
    hwnd = GetParent(root.winfo_id())
    style = GetWindowLong(hwnd, GWL_EXSTYLE)
    if enable:
        style |= WS_EX_TRANSPARENT
    else:
        style &= ~WS_EX_TRANSPARENT
    SetWindowLong(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TOPMOST)
    SetLayeredWindowAttributes(hwnd, 0, label_opacity, LWA_ALPHA)

# ─────────────────────────────────────────────
# 트레이 아이콘 관련
def create_icon_image():
    img = Image.new("RGB", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((16, 16, 48, 48), fill="red")
    return img

def toggle_details(icon=None, item=None):
    global details_visible
    details_visible = not details_visible

    if details_visible:
        info_frame0.pack(side="left", anchor="w")
    else:
        info_frame0.pack_forget()

    save_config()
def toggle_lock(icon=None, item=None):
    global locked, label_opacity
    locked = not locked
    set_click_through(locked)
    set_opacity(label_opacity)
    save_config()

def exit_app(icon, item):
    icon.stop()
    root.destroy()

def setup_tray():
    menu = Menu(
        MenuItem(lambda icon: "👁️ 상세정보 숨기기" if details_visible else "👁️ 상세정보 보이기", toggle_details),
        MenuItem(lambda icon: "🔒 잠금 해제" if locked else "🔒 잠금", toggle_lock),
        MenuItem("❌ 종료", exit_app)
    )
    icon = Icon("StatusOverlay", create_icon_image(), "상태표시기", menu)
    threading.Thread(target=icon.run, daemon=True).start()

# ─────────────────────────────────────────────
# 초기 설정
config = load_config()
label_font_size = config["font_size"]
label_opacity = config["opacity"]
locked = config["locked"]
details_visible = config["details_visible"]
# ─────────────────────────────────────────────
# tkinter 창 설정
root = tk.Tk()
root.overrideredirect(True)
root.wm_attributes("-topmost", True)
root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
root.config(bg=TRANSPARENT_COLOR)
root.geometry(f"+{config['x']}+{config['y']}")

# 전체 프레임
frame = tk.Frame(root, bg=TRANSPARENT_COLOR)
frame.pack()

# 왼쪽: 상태 표시 (크게)
label_status = tk.Label(frame, text="대기", font=(BIG_FONT, label_font_size), fg="red", bg=TRANSPARENT_COLOR)
label_status.pack(side="left", anchor="center", padx=10)

info_frame0 = tk.Frame(frame, bg=TRANSPARENT_COLOR)
info_frame0.pack(side="left", anchor="w")

# 오른쪽: 정보 표시 (작게, 세로 2줄)
info_frame1 = tk.Frame(info_frame0, bg=TRANSPARENT_COLOR)
info_frame1.pack(anchor="w", pady=(0,0))

label_info_01 = tk.Label(info_frame1, text="잔여", font=(SMALL_FONT_0, label_font_size // 3), fg="white", bg=TRANSPARENT_COLOR)
label_info_01.pack(side="left", anchor="w")#, pady=(11,0))

label_info_1 = tk.Label(info_frame1, text="", font=(SMALL_FONT_1, label_font_size // 3), fg="white", bg=TRANSPARENT_COLOR)
label_info_1.pack(side="left", anchor="w")#, pady=(11,0))

info_frame2 = tk.Frame(info_frame0, bg=TRANSPARENT_COLOR)
info_frame2.pack(anchor="w", pady=(0,0))

label_info_02 = tk.Label(info_frame2, text="퇴근", font=(SMALL_FONT_0, label_font_size // 3), fg="white", bg=TRANSPARENT_COLOR)
label_info_02.pack(side="left", anchor="e")#, pady=(0,0))

label_info_2 = tk.Label(info_frame2, text="", font=(SMALL_FONT_1, label_font_size // 3), fg="white", bg=TRANSPARENT_COLOR)
label_info_2.pack(side="left", anchor="w")#, pady=(0,0))
# ─────────────────────────────────────────────
# 창 이동
def start_move(event):
    if not locked:
        root.x = event.x
        root.y = event.y

def do_move(event):
    if not locked:
        x = event.x_root - root.x
        y = event.y_root - root.y
        root.geometry(f"+{x}+{y}")

label_status.bind("<Button-1>", start_move)
label_status.bind("<B1-Motion>", do_move)

# ─────────────────────────────────────────────
# 키 입력 처리
def key_event(event):
    global label_font_size, label_opacity, locked
    if event.keysym in ("plus", "equal", "KP_Add"):
        label_font_size += 4
    elif event.keysym in ("minus", "underscore", "KP_Subtract"):
        label_font_size = max(8, label_font_size - 4)
    elif event.keysym == "Up":
        label_opacity = min(255, label_opacity + 10)
    elif event.keysym == "Down":
        label_opacity = max(55, label_opacity - 10)
    # elif event.keysym.lower() == "l":
    #     locked = not locked
    #     set_click_through(locked)

    # 갱신
    label_status.config(font=(BIG_FONT, label_font_size))
    label_info_01.config(font=(SMALL_FONT_0, label_font_size // 3))
    label_info_02.config(font=(SMALL_FONT_0, label_font_size // 3))
    label_info_1.config(font=(SMALL_FONT_1, label_font_size // 3))
    label_info_2.config(font=(SMALL_FONT_1, label_font_size // 3))
    set_opacity(label_opacity)
    save_config()

root.bind("<Key>", key_event)
root.focus_force()

# ─────────────────────────────────────────────
# 실행
print("[실행 경로]", os.getcwd())
print("[찾는 경로]", FILE_PATH)
print("[존재하는 파일]", glob.glob(FILE_PATH))

set_opacity(label_opacity)
set_click_through(locked)
setup_tray()
threading.Thread(target=update_labels, daemon=True).start()
root.mainloop()

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
TRANSPARENT_COLOR = "black"
BIG_FONT = ("Pretendard Semibold", 64)
TEST_FONT = ("Pretendard", 24)
SMALL_FONT = ("나눔고딕코딩", 24)
CONFIG_PATH = "config.json"
DEFAULT_CONFIG = {
    "x": 100,
    "y": 100,
    "font_size": 64,
    "opacity": 255,
    "locked": False,
    "details_visible": True
}
details_visible = True
lunch_time = timedelta(hours=12)
dinner_time = timedelta(hours=18)
one_hours = timedelta(hours=1)
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
    # "06시 54분분" → timedelta
    hour_match = re.search(r'(\d+)\s*시', s)
    minute_match = re.search(r'(\d+)\s*분', s)

    h = int(hour_match.group(1)) if hour_match else None
    m = int(minute_match.group(1)) if minute_match else None
    return timedelta(hours=h, minutes=m)

def split_timedelta(td: timedelta):
    total_minutes = int(td.total_seconds() // 60)
    return total_minutes // 60, total_minutes % 60

# ─────────────────────────────────────────────
# 상태 판단 + 정보 추출
def get_status_and_times():
    latest = sorted(glob.glob("../page_content_*.json"))[-1]
    with open(latest, 'r', encoding='utf-8') as f:
        data = json.load(f)
    current_time = data.get("saved_at")
    current_time= parse_korean_time(current_time)

    content = data.get("content", "")
    contents = content.split("\n")

    remain_time = None
    today_time = None
    start_time = None
    finish_time = None

    status = "출근"
    label_1 = ""
    label_2 = ""

    for idx, item in enumerate(contents):
        if "금주 잔여 복무시간" in item:
            remain_time = parse_duration(contents[idx+1])
        elif "출근시간" in item:
            if "예상 누적"  in contents[idx+1]:
                start_time = parse_colon_time(contents[idx+2])
                today_time = parse_colon_time(contents[idx+1].split(" ")[-1])
        elif "퇴근시간" in item:
            if not "스케줄" in contents[idx+1]:
                finish_time = parse_colon_time(contents[idx+1])
                
    remain_h, remain_m = split_timedelta(remain_time)
    label_1 = f"{remain_h:02d}:{remain_m:02d}"

    if (start_time is not None) and (finish_time is None): # 출근
        status = "출근"
    elif (start_time is not None) and (finish_time is not None): # 자정 넘기기전에 퇴근한 경우
        status = "퇴근"
        finish_h, finish_m = split_timedelta(finish_time)
        label_2 = f"{finish_h:02d}:{finish_m:02d}"
        return status, label_1, label_2
    elif (start_time is None) and (finish_time is None): # 자정을 넘겼거나 아직 출근 안함
        status = "퇴근"
        label_2 = "출근이나 해"
        return status, label_1, label_2
    else: # 이거 뜨면 진짜 뭐지 찾아봐야함
        status = "뭐지"

    if today_time is None:
        real_time = remain_time
    else:
        real_time = remain_time - today_time

    real_h, real_m = split_timedelta(real_time)
    label_1 = f"{real_h:02d}:{real_m:02d}"

    end_time = current_time + real_time

    if (end_time >= lunch_time) and (current_time < lunch_time):
        end_time += one_hours
    elif (end_time >= lunch_time) and (current_time > lunch_time) and (current_time < (lunch_time + one_hours)):
        end_time += (lunch_time + one_hours - current_time)

    if (end_time >= dinner_time) and (current_time < dinner_time):
        end_time += one_hours
    elif (end_time >= dinner_time) and (current_time > dinner_time) and (current_time < (dinner_time + one_hours)):
        end_time += (dinner_time + one_hours - current_time)

    end_h, end_m = split_timedelta(end_time)


    if remain_time > timedelta(hours=12):
        label_2 = "오늘 못 채워"
    else:
        if start_time is None:
            label_2 = "출근이나 해"
        else:
            label_2 = f"{end_h:02d}:{end_m:02d}"

    os.remove(latest)
    return status, label_1, label_2

# ─────────────────────────────────────────────
# UI 갱신
def update_labels():
    while True:
        try:
            latest = sorted(glob.glob("../page_content_*.json"))[-1]
            with open(latest, 'r', encoding='utf-8') as f:
                data = json.load(f)
            status, remaining, target_time = get_status_and_times()
            label_status.config(text=status)
            label_info_1.config(text=remaining if remaining else "")
            label_info_2.config(text=target_time if target_time else "")
        except:
            pass
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
    global locked
    locked = not locked
    set_click_through(locked)
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
label_status = tk.Label(frame, text="대기", font=BIG_FONT, fg="red", bg=TRANSPARENT_COLOR)
label_status.pack(side="left", anchor="center", padx=10)

info_frame0 = tk.Frame(frame, bg=TRANSPARENT_COLOR)
info_frame0.pack(side="left", anchor="w")

# 오른쪽: 정보 표시 (작게, 세로 2줄)
info_frame1 = tk.Frame(info_frame0, bg=TRANSPARENT_COLOR)
info_frame1.pack(anchor="w", pady=(0,0))

label_info_01 = tk.Label(info_frame1, text="남은시간", font=TEST_FONT, fg="white", bg=TRANSPARENT_COLOR)
label_info_01.pack(side="left", anchor="w")#, pady=(11,0))

label_info_1 = tk.Label(info_frame1, text="", font=SMALL_FONT, fg="white", bg=TRANSPARENT_COLOR)
label_info_1.pack(side="left", anchor="w")#, pady=(11,0))

info_frame2 = tk.Frame(info_frame0, bg=TRANSPARENT_COLOR)
info_frame2.pack(anchor="w", pady=(0,0))

label_info_02 = tk.Label(info_frame2, text="퇴근시각", font=TEST_FONT, fg="white", bg=TRANSPARENT_COLOR)
label_info_02.pack(side="left", anchor="e")#, pady=(0,0))

label_info_2 = tk.Label(info_frame2, text="", font=SMALL_FONT, fg="white", bg=TRANSPARENT_COLOR)
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
    if event.keysym == "plus" or event.keysym == "KP_Add":
        label_font_size += 4
    elif event.keysym == "minus" or event.keysym == "KP_Subtract":
        label_font_size = max(8, label_font_size - 4)
    elif event.keysym == "Up":
        label_opacity = min(255, label_opacity + 10)
    elif event.keysym == "Down":
        label_opacity = max(50, label_opacity - 10)
    elif event.keysym.lower() == "l":
        locked = not locked
        set_click_through(locked)

    # 갱신
    label_status.config(font=("Pretendard SemiBold", label_font_size))
    label_info_1.config(font=("Pretendard", label_font_size // 3))
    label_info_2.config(font=("Pretendard", label_font_size // 3))
    set_opacity(label_opacity)
    save_config()

root.bind("<Key>", key_event)
root.focus_force()

# ─────────────────────────────────────────────
# 실행
set_opacity(label_opacity)
set_click_through(locked)
setup_tray()
threading.Thread(target=update_labels, daemon=True).start()
root.mainloop()

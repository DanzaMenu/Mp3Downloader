# Version: 1.0.2

import sys
import os
import json
import time
import subprocess
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QProgressBar, QListWidget, QListWidgetItem, QMessageBox, QCheckBox, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QColor, QLinearGradient, QPainter, QBrush, QPen
import yt_dlp

# ── App identity ───────────────────────────────────────────────────────────────
CURRENT_VERSION = "1.0.2"
GITHUB_API_URL  = "https://api.github.com/repos/DanzaMenu/Mp3Downloader/releases/latest"
SCRIPT_PATH     = os.path.abspath(__file__)
SCRIPT_DIR      = os.path.dirname(SCRIPT_PATH)
REAL_APP_NAME   = "mp3_downloader.py"
UPDATE_FILENAME = "mp3_downloader_update.py"
UPDATE_FILE     = os.path.join(SCRIPT_DIR, UPDATE_FILENAME)

WORKING_DIR = SCRIPT_DIR
MP3_DIR = os.path.join(WORKING_DIR, "Mp3s")
MAX_RETRIES = 5

# ── Update helpers ─────────────────────────────────────────────────────────────
def _parse_version(v: str):
    return tuple(int(x) for x in v.lstrip("v").split("."))

def handle_update_file():
    if os.path.basename(SCRIPT_PATH) == UPDATE_FILENAME:
        target = os.path.join(SCRIPT_DIR, REAL_APP_NAME)
        time.sleep(1.5)
        try:
            os.replace(SCRIPT_PATH, target)
        except Exception as e:
            print(f"[updater] replace failed: {e}", file=sys.stderr)
            sys.exit(1)
        subprocess.Popen(
            [sys.executable, target],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        sys.exit(0)

def cleanup_update_file():
    if os.path.exists(UPDATE_FILE):
        try:
            os.remove(UPDATE_FILE)
        except Exception:
            pass
        return True
    return False

def fetch_update_info():
    req = urllib.request.Request(GITHUB_API_URL, headers={"User-Agent": "AppUpdater"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode())
    latest_tag = data.get("tag_name", "").lstrip("v")
    assets = data.get("assets", [])
    dl_url = next(
        (a["browser_download_url"] for a in assets if a["name"] == REAL_APP_NAME), None
    )
    return latest_tag, dl_url

def download_update(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "AppUpdater"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(UPDATE_FILE, "wb") as f:
        f.write(data)


class Signals(QObject):
    status_update = pyqtSignal(str, str)
    progress_update = pyqtSignal(int, str)
    queue_item_update = pyqtSignal(int, str)   # row index, state: "downloading"|"done"|"failed"
    download_finished = pyqtSignal()


signals = Signals()


BROWSERS = ["edge", "firefox", "chrome", "brave", "chromium", "vivaldi", "safari"]
COOKIES_FILE = os.path.join(WORKING_DIR, "cookies.txt")


def _progress_hook(d):
    status = d.get("status", "")
    if status == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
        downloaded = d.get("downloaded_bytes", 0)
        speed = d.get("speed") or 0
        eta = d.get("eta") or 0
        pct = int(downloaded / total * 100) if total else -1
        speed_str = f"{speed/1024:.0f} KB/s" if speed else ""
        eta_str = f"  ETA {eta}s" if eta else ""
        label = f"Downloading...  {pct}%  {speed_str}{eta_str}" if pct >= 0 else "Downloading..."
        signals.progress_update.emit(pct, label)
    elif status == "finished":
        signals.progress_update.emit(99, "Converting to MP3...")


def _build_opts(browser=None, cookies_file=None):
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(MP3_DIR, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_progress_hook],
    }
    if cookies_file:
        opts["cookiefile"] = cookies_file
    elif browser:
        opts["cookiesfrombrowser"] = (browser, None, None, None)
    return opts


def _get_cookie_sources():
    sources = []
    # cookies.txt file takes priority if it exists
    if os.path.exists(COOKIES_FILE):
        sources.append(("cookies.txt", _build_opts(cookies_file=COOKIES_FILE)))
    # then try each browser
    for b in BROWSERS:
        sources.append((b, _build_opts(browser=b)))
    # last resort: no cookies
    sources.append((None, _build_opts()))
    return sources


def _download_one(url: str) -> bool:
    cookie_sources = _get_cookie_sources()
    for attempt in range(1, MAX_RETRIES + 1):
        for source_name, ydl_opts in cookie_sources:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "Unknown")
                signals.status_update.emit(f"Saved:  {title}.mp3", "#57f287")
                return True
            except Exception:
                continue
    return False


def download_queue(urls: list, thread_count: int = 1):
    os.makedirs(MP3_DIR, exist_ok=True)
    total = len(urls)
    completed = [0]
    lock = threading.Lock()

    def _task(idx, url):
        signals.queue_item_update.emit(idx, "downloading")
        ok = _download_one(url)
        signals.queue_item_update.emit(idx, "done" if ok else "failed")
        with lock:
            completed[0] += 1
            pct = int(completed[0] / total * 100)
        signals.progress_update.emit(pct, f"Downloaded {completed[0]} of {total}...")
        return ok

    with ThreadPoolExecutor(max_workers=thread_count) as pool:
        futures = {pool.submit(_task, i, url): url for i, url in enumerate(urls)}
        for future in as_completed(futures):
            if not future.result():
                signals.status_update.emit(f"Failed: {futures[future][:60]}", "#ed4245")

    signals.progress_update.emit(100, f"Done — {total} file{'s' if total != 1 else ''} saved.")
    signals.download_finished.emit()


CONFIG_FILE = os.path.join(WORKING_DIR, "config.json")

THEMES = {
    "Deep Space": {
        "bg": [(16,8,38,235),(26,10,52,225),(12,6,32,235)],
        "border": (140,80,255,70),
        "sheen": (255,255,255,18),
        "icon": "rgba(180,120,255,220)",
        "title": "rgba(255,255,255,210)",
        "input_bg": "rgba(255,255,255,10)",
        "input_border": "rgba(180,120,255,70)",
        "input_border_focus": "rgba(180,120,255,200)",
        "input_sel": "rgba(130,80,255,160)",
        "add_btn": (100,40,220,60,15,180),
        "dl_btn": (130,55,255,75,25,200),
        "clear_bg": "rgba(255,255,255,12)",
        "clear_border": "rgba(180,120,255,70)",
        "clear_color": "rgba(220,200,255,180)",
        "list_bg": "rgba(255,255,255,8)",
        "list_border": "rgba(180,120,255,50)",
        "list_sel": "rgba(130,55,255,120)",
        "list_text": "rgba(220,220,220,220)",
        "scrollbar": "rgba(180,120,255,120)",
        "check_border": "rgba(180,120,255,100)",
        "check_start": "rgba(130,55,255,220)",
        "check_end": "rgba(75,25,200,200)",
        "spin_border": "rgba(180,120,255,70)",
        "spin_border_focus": "rgba(180,120,255,200)",
        "prog_bg": "rgba(255,255,255,30)",
        "prog_border": "rgba(180,120,255,40)",
        "prog_start": "rgba(120,45,240,230)",
        "prog_end": "rgba(200,110,255,255)",
        "status": "rgba(200,200,200,160)",
        "thread_lbl": "rgba(200,200,200,160)",
        "combo_bg": "rgba(255,255,255,10)",
        "combo_border": "rgba(180,120,255,70)",
        "combo_color": "rgba(200,180,255,200)",
    },
    "Matrix": {
        "bg": [(0,0,0,245),(4,12,4,240),(0,0,0,245)],
        "border": (0,200,50,80),
        "sheen": (0,255,65,8),
        "icon": "rgba(0,255,65,220)",
        "title": "rgba(0,255,65,220)",
        "input_bg": "rgba(0,255,65,6)",
        "input_border": "rgba(0,200,50,100)",
        "input_border_focus": "rgba(0,255,65,220)",
        "input_sel": "rgba(0,180,40,160)",
        "add_btn": (0,140,30,0,100,20),
        "dl_btn": (0,160,35,0,110,25),
        "clear_bg": "rgba(0,255,65,8)",
        "clear_border": "rgba(0,200,50,80)",
        "clear_color": "rgba(0,255,65,200)",
        "list_bg": "rgba(0,255,65,5)",
        "list_border": "rgba(0,200,50,60)",
        "list_sel": "rgba(0,180,40,100)",
        "list_text": "rgba(0,255,65,220)",
        "scrollbar": "rgba(0,200,50,140)",
        "check_border": "rgba(0,200,50,120)",
        "check_start": "rgba(0,180,40,220)",
        "check_end": "rgba(0,120,25,200)",
        "spin_border": "rgba(0,200,50,100)",
        "spin_border_focus": "rgba(0,255,65,220)",
        "prog_bg": "rgba(0,255,65,15)",
        "prog_border": "rgba(0,200,50,60)",
        "prog_start": "rgba(0,180,40,230)",
        "prog_end": "rgba(0,255,65,255)",
        "status": "rgba(0,255,65,180)",
        "thread_lbl": "rgba(0,255,65,160)",
        "combo_bg": "rgba(0,255,65,8)",
        "combo_border": "rgba(0,200,50,80)",
        "combo_color": "rgba(0,255,65,200)",
    },
    "Neon Arcade": {
        "bg": [(5,0,15,245),(10,0,20,240),(5,0,12,245)],
        "border": (255,0,128,100),
        "sheen": (255,0,200,10),
        "icon": "rgba(0,240,255,230)",
        "title": "rgba(255,0,200,230)",
        "input_bg": "rgba(255,0,128,6)",
        "input_border": "rgba(255,0,128,100)",
        "input_border_focus": "rgba(0,240,255,220)",
        "input_sel": "rgba(255,0,128,140)",
        "add_btn": (0,180,220,0,100,160),
        "dl_btn": (200,0,160,120,0,220),
        "clear_bg": "rgba(255,255,255,8)",
        "clear_border": "rgba(255,0,128,80)",
        "clear_color": "rgba(255,80,200,200)",
        "list_bg": "rgba(255,0,128,5)",
        "list_border": "rgba(255,0,128,60)",
        "list_sel": "rgba(200,0,160,120)",
        "list_text": "rgba(0,240,255,220)",
        "scrollbar": "rgba(255,0,128,140)",
        "check_border": "rgba(255,0,128,120)",
        "check_start": "rgba(200,0,160,220)",
        "check_end": "rgba(0,180,220,200)",
        "spin_border": "rgba(255,0,128,100)",
        "spin_border_focus": "rgba(0,240,255,220)",
        "prog_bg": "rgba(255,0,128,15)",
        "prog_border": "rgba(255,0,128,60)",
        "prog_start": "rgba(255,220,0,230)",
        "prog_end": "rgba(255,0,200,255)",
        "status": "rgba(0,240,255,180)",
        "thread_lbl": "rgba(255,80,200,160)",
        "combo_bg": "rgba(255,0,128,8)",
        "combo_border": "rgba(255,0,128,80)",
        "combo_color": "rgba(0,240,255,200)",
    },
    "Glass": {
        "bg": [(255,255,255,18),(240,240,255,14),(255,255,255,18)],
        "border": (255,255,255,90),
        "sheen": (255,255,255,30),
        "icon": "rgba(255,255,255,180)",
        "title": "rgba(255,255,255,220)",
        "input_bg": "rgba(255,255,255,15)",
        "input_border": "rgba(255,255,255,80)",
        "input_border_focus": "rgba(255,255,255,200)",
        "input_sel": "rgba(200,200,255,120)",
        "add_btn": (220,220,240,180,180,210),
        "dl_btn": (200,200,230,160,160,210),
        "clear_bg": "rgba(255,255,255,12)",
        "clear_border": "rgba(255,255,255,70)",
        "clear_color": "rgba(255,255,255,200)",
        "list_bg": "rgba(255,255,255,10)",
        "list_border": "rgba(255,255,255,60)",
        "list_sel": "rgba(200,200,255,80)",
        "list_text": "rgba(255,255,255,220)",
        "scrollbar": "rgba(255,255,255,120)",
        "check_border": "rgba(255,255,255,100)",
        "check_start": "rgba(220,220,255,200)",
        "check_end": "rgba(180,180,220,180)",
        "spin_border": "rgba(255,255,255,80)",
        "spin_border_focus": "rgba(255,255,255,200)",
        "prog_bg": "rgba(255,255,255,25)",
        "prog_border": "rgba(255,255,255,50)",
        "prog_start": "rgba(200,200,240,220)",
        "prog_end": "rgba(255,255,255,255)",
        "status": "rgba(255,255,255,180)",
        "thread_lbl": "rgba(255,255,255,160)",
        "combo_bg": "rgba(255,255,255,12)",
        "combo_border": "rgba(255,255,255,70)",
        "combo_color": "rgba(255,255,255,200)",
    },
    "Christmas": {
        "bg": [(5,20,5,245),(18,5,5,240),(5,18,5,245)],
        "border": (220,40,40,100),
        "sheen": (255,215,0,10),
        "icon": "rgba(255,215,0,230)",
        "title": "rgba(255,215,0,230)",
        "input_bg": "rgba(255,215,0,6)",
        "input_border": "rgba(220,40,40,100)",
        "input_border_focus": "rgba(255,215,0,220)",
        "input_sel": "rgba(180,30,30,160)",
        "add_btn": (10,100,20,5,70,10),
        "dl_btn": (180,20,20,120,10,10),
        "clear_bg": "rgba(255,215,0,10)",
        "clear_border": "rgba(220,40,40,80)",
        "clear_color": "rgba(255,215,0,210)",
        "list_bg": "rgba(0,80,0,12)",
        "list_border": "rgba(220,40,40,60)",
        "list_sel": "rgba(180,20,20,120)",
        "list_text": "rgba(255,230,180,220)",
        "scrollbar": "rgba(220,40,40,140)",
        "check_border": "rgba(255,215,0,120)",
        "check_start": "rgba(220,40,40,220)",
        "check_end": "rgba(10,100,20,200)",
        "spin_border": "rgba(220,40,40,100)",
        "spin_border_focus": "rgba(255,215,0,220)",
        "prog_bg": "rgba(255,215,0,15)",
        "prog_border": "rgba(220,40,40,60)",
        "prog_start": "rgba(10,120,20,230)",
        "prog_end": "rgba(220,40,40,255)",
        "status": "rgba(255,215,0,180)",
        "thread_lbl": "rgba(255,215,0,160)",
        "combo_bg": "rgba(255,215,0,8)",
        "combo_border": "rgba(220,40,40,80)",
        "combo_color": "rgba(255,215,0,200)",
    },
    "Midnight Gold": {
        "bg": [(8,8,8,245),(14,12,4,240),(6,6,6,245)],
        "border": (200,160,40,80),
        "sheen": (255,215,0,12),
        "icon": "rgba(255,200,40,220)",
        "title": "rgba(255,210,60,220)",
        "input_bg": "rgba(255,200,40,6)",
        "input_border": "rgba(200,160,40,90)",
        "input_border_focus": "rgba(255,210,60,220)",
        "input_sel": "rgba(180,130,20,160)",
        "add_btn": (160,110,10,110,75,5),
        "dl_btn": (200,150,20,140,100,10),
        "clear_bg": "rgba(255,200,40,8)",
        "clear_border": "rgba(200,160,40,70)",
        "clear_color": "rgba(255,210,60,190)",
        "list_bg": "rgba(255,200,40,5)",
        "list_border": "rgba(200,160,40,50)",
        "list_sel": "rgba(180,130,20,120)",
        "list_text": "rgba(255,230,160,220)",
        "scrollbar": "rgba(200,160,40,140)",
        "check_border": "rgba(200,160,40,110)",
        "check_start": "rgba(200,150,20,220)",
        "check_end": "rgba(140,100,10,200)",
        "spin_border": "rgba(200,160,40,90)",
        "spin_border_focus": "rgba(255,210,60,220)",
        "prog_bg": "rgba(255,200,40,15)",
        "prog_border": "rgba(200,160,40,50)",
        "prog_start": "rgba(180,130,15,230)",
        "prog_end": "rgba(255,210,60,255)",
        "status": "rgba(255,210,60,180)",
        "thread_lbl": "rgba(200,170,80,160)",
        "combo_bg": "rgba(255,200,40,8)",
        "combo_border": "rgba(200,160,40,70)",
        "combo_color": "rgba(255,210,60,200)",
    },
    "Cyberpunk": {
        "bg": [(8,8,15,245),(14,12,20,240),(5,5,12,245)],
        "border": (255,200,0,80),
        "sheen": (255,180,0,10),
        "icon": "rgba(255,200,0,230)",
        "title": "rgba(255,210,0,230)",
        "input_bg": "rgba(255,200,0,6)",
        "input_border": "rgba(255,180,0,90)",
        "input_border_focus": "rgba(255,210,0,230)",
        "input_sel": "rgba(200,140,0,160)",
        "add_btn": (180,120,0,120,80,0),
        "dl_btn": (200,140,0,140,90,0),
        "clear_bg": "rgba(255,200,0,8)",
        "clear_border": "rgba(255,180,0,70)",
        "clear_color": "rgba(255,220,0,190)",
        "list_bg": "rgba(255,200,0,5)",
        "list_border": "rgba(255,180,0,50)",
        "list_sel": "rgba(180,120,0,120)",
        "list_text": "rgba(255,230,100,220)",
        "scrollbar": "rgba(255,180,0,140)",
        "check_border": "rgba(255,180,0,110)",
        "check_start": "rgba(200,140,0,220)",
        "check_end": "rgba(140,90,0,200)",
        "spin_border": "rgba(255,180,0,90)",
        "spin_border_focus": "rgba(255,210,0,230)",
        "prog_bg": "rgba(255,200,0,15)",
        "prog_border": "rgba(255,180,0,50)",
        "prog_start": "rgba(220,120,0,230)",
        "prog_end": "rgba(255,220,0,255)",
        "status": "rgba(255,210,0,180)",
        "thread_lbl": "rgba(200,170,0,160)",
        "combo_bg": "rgba(255,200,0,8)",
        "combo_border": "rgba(255,180,0,70)",
        "combo_color": "rgba(255,220,0,200)",
    },
}


class GlassWidget(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(255, 255, 255, 18))
        grad.setColorAt(1.0, QColor(255, 255, 255, 6))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)


BTN_STYLE = """
    QPushButton {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba({r0},{g0},{b0},200), stop:1 rgba({r1},{g1},{b1},180));
        border: 1px solid rgba(180,120,255,110);
        border-radius: 10px;
        color: #FFFFFF;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba({rh0},{gh0},{bh0},230), stop:1 rgba({rh1},{gh1},{bh1},210));
        border: 1px solid rgba(200,150,255,150);
    }}
    QPushButton:pressed {{
        background: rgba(60,20,160,210);
    }}
    QPushButton:disabled {{
        background: rgba(70,70,90,100);
        border: 1px solid rgba(120,120,140,50);
        color: rgba(200,200,200,80);
    }}
    QPushButton:focus {{ outline: none; }}
"""

def _btn_style(r0, g0, b0, r1, g1, b1, rh0=None, gh0=None, bh0=None, rh1=None, gh1=None, bh1=None):
    rh0 = rh0 or min(r0 + 30, 255)
    gh0 = gh0 or min(g0 + 30, 255)
    bh0 = bh0 or min(b0 + 10, 255)
    rh1 = rh1 or min(r1 + 25, 255)
    gh1 = gh1 or min(g1 + 20, 255)
    bh1 = bh1 or min(b1 + 20, 255)
    return BTN_STYLE.format(r0=r0,g0=g0,b0=b0,r1=r1,g1=g1,b1=b1,
                             rh0=rh0,gh0=gh0,bh0=bh0,rh1=rh1,gh1=gh1,bh1=bh1)


class MainWindow(QMainWindow):
    def __init__(self, just_updated: bool = False):
        super().__init__()
        self._just_updated = just_updated
        self.setWindowTitle("Mp3 Downloader")
        self.setFixedSize(620, 340)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None
        self._theme = THEMES["Deep Space"]

        central = GlassWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(8)

        # ── Title row ──────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        self.icon_lbl = QLabel("♪")
        self.icon_lbl.setFont(QFont("Tahoma", 13))
        self.icon_lbl.setStyleSheet("color: rgba(180,120,255,220);")
        self.icon_lbl.setFixedWidth(22)

        self.title_lbl = QLabel(f"Mp3 Downloader  |  v{CURRENT_VERSION}  -  Checking...")
        self.title_lbl.setFont(QFont("Tahoma", 10))
        self.title_lbl.setStyleSheet("color: rgba(255,255,255,210); font-weight: bold;")

        close_btn = QPushButton("×")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,10);
                border: 1px solid rgba(255,255,255,25);
                border-radius: 13px;
                color: rgba(255,255,255,160);
                font-size: 13pt;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover { background: rgba(237,66,69,200); color: white; border: none; }
            QPushButton:focus { outline: none; }
        """)
        close_btn.clicked.connect(self.close)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setFixedHeight(24)
        self.theme_combo.setFont(QFont("Tahoma", 7))
        self.theme_combo.setFixedWidth(110)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        title_row.addWidget(self.icon_lbl)
        title_row.addWidget(self.title_lbl)
        title_row.addStretch()
        title_row.addWidget(self.theme_combo)
        title_row.addWidget(close_btn)
        root.addLayout(title_row)

        # ── URL input + Add button ─────────────────────────────────
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a video URL here...")
        self.url_input.setFixedHeight(36)
        self.url_input.setFont(QFont("Tahoma", 9))
        self.url_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,10);
                border: 1px solid rgba(180,120,255,70);
                border-radius: 10px;
                color: #FFFFFF;
                padding: 0px 14px;
                selection-background-color: rgba(130,80,255,160);
            }
            QLineEdit:focus {
                border: 1px solid rgba(180,120,255,200);
                background: rgba(255,255,255,15);
                outline: none;
            }
        """)
        self.url_input.returnPressed.connect(self._add_to_queue)

        self.add_btn = QPushButton("Add")
        self.add_btn.setFixedSize(72, 36)
        self.add_btn.setFont(QFont("Tahoma", 9))
        self.add_btn.setStyleSheet(_btn_style(100, 40, 220, 60, 15, 180))
        self.add_btn.clicked.connect(self._add_to_queue)

        input_row.addWidget(self.url_input)
        input_row.addWidget(self.add_btn)
        root.addLayout(input_row)

        # ── Clipboard watch checkbox ───────────────────────────────
        self.clip_check = QCheckBox("Auto-add copied links")
        self.clip_check.setFont(QFont("Tahoma", 8))
        self.clip_check.setStyleSheet("""
            QCheckBox {
                color: rgba(200,200,200,170);
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid rgba(180,120,255,100);
                border-radius: 3px;
                background: rgba(255,255,255,8);
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(130,55,255,220), stop:1 rgba(75,25,200,200));
                border: 1px solid rgba(180,120,255,180);
                image: none;
            }
            QCheckBox::indicator:hover {
                border: 1px solid rgba(180,120,255,200);
            }
        """)
        self.clip_check.stateChanged.connect(self._on_clip_toggle)
        root.addWidget(self.clip_check)

        self._last_clip = ""
        self._clip_timer = QTimer()
        self._clip_timer.setInterval(500)
        self._clip_timer.timeout.connect(self._poll_clipboard)

        # ── Queue list ────────────────────────────────────────────
        self.queue_list = QListWidget()
        self.queue_list.setFont(QFont("Tahoma", 8))
        self.queue_list.setFixedHeight(130)
        self.queue_list.setStyleSheet("""
            QListWidget {
                background: rgba(255,255,255,8);
                border: 1px solid rgba(180,120,255,50);
                border-radius: 10px;
                color: rgba(220,220,220,220);
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background: rgba(130,55,255,120);
                color: white;
            }
            QListWidget::item:hover:!selected {
                background: rgba(255,255,255,10);
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,8);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(180,120,255,120);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self.queue_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        root.addWidget(self.queue_list)

        # ── Clear + threads + Download All ────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.setFont(QFont("Tahoma", 9))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,12);
                border: 1px solid rgba(180,120,255,70);
                border-radius: 10px;
                color: rgba(220,200,255,180);
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(237,66,69,160);
                border: 1px solid rgba(237,66,69,200);
                color: white;
            }
            QPushButton:pressed { background: rgba(180,30,40,200); }
            QPushButton:disabled { opacity: 0.4; }
            QPushButton:focus { outline: none; }
        """)
        self.clear_btn.clicked.connect(self._clear_queue)

        self.thread_lbl = QLabel("Threads:")
        self.thread_lbl.setFont(QFont("Tahoma", 8))
        self.thread_lbl.setStyleSheet("color: rgba(200,200,200,160);")

        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 10)
        self.thread_spin.setValue(1)
        self.thread_spin.setFixedSize(52, 36)
        self.thread_spin.setFont(QFont("Tahoma", 9))
        self.thread_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255,255,255,10);
                border: 1px solid rgba(180,120,255,70);
                border-radius: 10px;
                color: #FFFFFF;
                padding: 0px 6px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0; border: none;
            }
            QSpinBox:focus { outline: none; border: 1px solid rgba(180,120,255,200); }
        """)

        self.dl_btn = QPushButton("Download All")
        self.dl_btn.setFixedHeight(36)
        self.dl_btn.setFont(QFont("Tahoma", 9))
        self.dl_btn.setStyleSheet(_btn_style(130, 55, 255, 75, 25, 200))
        self.dl_btn.clicked.connect(self._start_download)

        action_row.addWidget(self.clear_btn, stretch=1)
        action_row.addWidget(self.thread_lbl)
        action_row.addWidget(self.thread_spin)
        action_row.addWidget(self.dl_btn, stretch=3)
        root.addLayout(action_row)
        self.thread_spin.valueChanged.connect(lambda _: self._save_config())

        # ── Progress bar ───────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,30);
                border: 1px solid rgba(180,120,255,40);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(120,45,240,230), stop:1 rgba(200,110,255,255));
                border-radius: 3px;
            }
        """)
        root.addWidget(self.progress_bar)

        # ── Status label ───────────────────────────────────────────
        self.status_lbl = QLabel("Ready.")
        self.status_lbl.setFont(QFont("Tahoma", 8))
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: rgba(200,200,200,160);")
        root.addWidget(self.status_lbl)

        signals.status_update.connect(self._on_status)
        signals.progress_update.connect(self._on_progress)
        signals.queue_item_update.connect(self._on_queue_item)
        signals.download_finished.connect(self._on_finished)

        # load saved config
        saved_theme = "Deep Space"
        try:
            cfg = json.loads(open(CONFIG_FILE, encoding="utf-8").read())
            saved_theme = cfg.get("theme", "Deep Space")
            self.thread_spin.blockSignals(True)
            self.thread_spin.setValue(max(1, min(10, int(cfg.get("threads", 1)))))
            self.thread_spin.blockSignals(False)
            self.clip_check.blockSignals(True)
            self.clip_check.setChecked(bool(cfg.get("clipboard", False)))
            self.clip_check.blockSignals(False)
            if self.clip_check.isChecked():
                self._clip_timer.start(500)
        except Exception:
            pass
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText(saved_theme if saved_theme in THEMES else "Deep Space")
        self.theme_combo.blockSignals(False)
        self.apply_theme(self.theme_combo.currentText())

        QTimer.singleShot(500, self._run_update_check)

    def paintEvent(self, event):
        t = self._theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = t["bg"]
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(*bg[0]))
        grad.setColorAt(0.5, QColor(*bg[1]))
        grad.setColorAt(1.0, QColor(*bg[2]))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(*t["border"]), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)

        sr, sg, sb, sa = t["sheen"]
        sheen = QLinearGradient(0, 0, 0, self.height() * 0.35)
        sheen.setColorAt(0.0, QColor(sr, sg, sb, sa))
        sheen.setColorAt(1.0, QColor(sr, sg, sb, 0))
        painter.setBrush(QBrush(sheen))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, int(-self.height() * 0.65)), 18, 18)

    def apply_theme(self, name: str):
        t = THEMES.get(name, THEMES["Deep Space"])
        self._theme = t
        self.update()

        self.icon_lbl.setStyleSheet(f"color: {t['icon']};")
        self.title_lbl.setStyleSheet(f"color: {t['title']}; font-weight: bold;")
        self.thread_lbl.setStyleSheet(f"color: {t['thread_lbl']};")

        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background: {t['input_bg']};
                border: 1px solid {t['input_border']};
                border-radius: 10px;
                color: #FFFFFF;
                padding: 0px 14px;
                selection-background-color: {t['input_sel']};
            }}
            QLineEdit:focus {{
                border: 1px solid {t['input_border_focus']};
                background: rgba(255,255,255,15);
                outline: none;
            }}
        """)

        r0,g0,b0,r1,g1,b1 = t["add_btn"]
        self.add_btn.setStyleSheet(_btn_style(r0,g0,b0,r1,g1,b1))

        r0,g0,b0,r1,g1,b1 = t["dl_btn"]
        self.dl_btn.setStyleSheet(_btn_style(r0,g0,b0,r1,g1,b1))

        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['clear_bg']};
                border: 1px solid {t['clear_border']};
                border-radius: 10px;
                color: {t['clear_color']};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(237,66,69,160);
                border: 1px solid rgba(237,66,69,200);
                color: white;
            }}
            QPushButton:pressed {{ background: rgba(180,30,40,200); }}
            QPushButton:disabled {{ opacity: 0.4; }}
            QPushButton:focus {{ outline: none; }}
        """)

        self.clip_check.setStyleSheet(f"""
            QCheckBox {{ color: {t['status']}; spacing: 6px; }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {t['check_border']};
                border-radius: 3px;
                background: rgba(255,255,255,8);
            }}
            QCheckBox::indicator:checked {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {t['check_start']}, stop:1 {t['check_end']});
                border: 1px solid {t['check_border']};
                image: none;
            }}
            QCheckBox::indicator:hover {{ border: 1px solid {t['input_border_focus']}; }}
        """)

        self.queue_list.setStyleSheet(f"""
            QListWidget {{
                background: {t['list_bg']};
                border: 1px solid {t['list_border']};
                border-radius: 10px;
                color: {t['list_text']};
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{ padding: 4px 8px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {t['list_sel']}; color: white; }}
            QListWidget::item:hover:!selected {{ background: rgba(255,255,255,10); }}
            QScrollBar:vertical {{
                background: rgba(255,255,255,8); width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scrollbar']}; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self.thread_spin.setStyleSheet(f"""
            QSpinBox {{
                background: {t['input_bg']};
                border: 1px solid {t['spin_border']};
                border-radius: 10px;
                color: #FFFFFF;
                padding: 0px 6px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
            QSpinBox:focus {{ outline: none; border: 1px solid {t['spin_border_focus']}; }}
        """)

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {t['prog_bg']};
                border: 1px solid {t['prog_border']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {t['prog_start']}, stop:1 {t['prog_end']});
                border-radius: 3px;
            }}
        """)

        self.status_lbl.setStyleSheet(f"color: {t['status']};")

        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                background: {t['combo_bg']};
                border: 1px solid {t['combo_border']};
                border-radius: 8px;
                color: {t['combo_color']};
                padding: 0px 8px;
            }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; }}
            QComboBox QAbstractItemView {{
                background: rgba(20,10,40,240);
                border: 1px solid {t['combo_border']};
                color: {t['combo_color']};
                selection-background-color: {t['list_sel']};
                outline: none;
            }}
            QComboBox:focus {{ outline: none; }}
        """)

    def _save_config(self):
        try:
            existing = {}
            try:
                existing = json.loads(open(CONFIG_FILE, encoding="utf-8").read())
            except Exception:
                pass
            existing["theme"] = self.theme_combo.currentText()
            existing["threads"] = self.thread_spin.value()
            existing["clipboard"] = self.clip_check.isChecked()
            open(CONFIG_FILE, "w", encoding="utf-8").write(json.dumps(existing))
        except Exception:
            pass

    def _on_theme_changed(self, name: str):
        self.apply_theme(name)
        self._save_config()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _run_update_check(self):
        if self._just_updated:
            self.title_lbl.setText(f"Mp3 Downloader  |  v{CURRENT_VERSION}")
            QMessageBox.information(self, "Updated!", f"Successfully updated to v{CURRENT_VERSION}!")
            return
        self._update_result = None
        self._update_error  = None
        def _check():
            try:
                self._update_result = fetch_update_info()
            except Exception as e:
                self._update_error = str(e)
            QTimer.singleShot(0, self._on_check_complete)
        threading.Thread(target=_check, daemon=True).start()

    def _on_check_complete(self):
        self.title_lbl.setText(f"Mp3 Downloader  |  v{CURRENT_VERSION}")
        if self._update_error:
            # 404 = no releases yet, silently ignore
            if "404" not in self._update_error and "HTTP Error 404" not in self._update_error:
                QMessageBox.warning(self, "Update Check Failed",
                    f"Could not check for updates:\n{self._update_error}")
            return
        latest, url = self._update_result
        if not latest or _parse_version(latest) <= _parse_version(CURRENT_VERSION):
            return  # up to date — no popup, just silently ready
        msg = QMessageBox(self)
        msg.setWindowTitle("Update Available")
        msg.setText(
            f"A new version is available: <b>v{latest}</b><br>"
            f"You are on v{CURRENT_VERSION}.<br><br>"
            f"Download and install now?"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            if not url:
                QMessageBox.warning(self, "Update Error", "No downloadable file found for this release.")
                return
            try:
                download_update(url)
                subprocess.Popen(
                    [sys.executable, UPDATE_FILE],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                )
                QApplication.quit()
            except Exception as e:
                QMessageBox.critical(self, "Update Failed", f"Download failed:\n{e}")

    def _on_clip_toggle(self, state):
        if state == Qt.CheckState.Checked.value:
            self._last_clip = QApplication.clipboard().text().strip()
            self._clip_timer.start()
        else:
            self._clip_timer.stop()
        self._save_config()

    def _poll_clipboard(self):
        text = QApplication.clipboard().text().strip()
        if text == self._last_clip:
            return
        self._last_clip = text
        if not text.startswith(("http://", "https://")):
            return
        # dupe check
        for i in range(self.queue_list.count()):
            if self.queue_list.item(i).data(Qt.ItemDataRole.UserRole) == text:
                return
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, text)
        self.queue_list.addItem(item)
        self.status_lbl.setStyleSheet("color: rgba(200,200,200,160);")
        self.status_lbl.setText(f"{self.queue_list.count()} URL{'s' if self.queue_list.count() != 1 else ''} queued.")

    def _add_to_queue(self):
        url = self.url_input.text().strip()
        if not url:
            return
        item = QListWidgetItem(url)
        item.setData(Qt.ItemDataRole.UserRole, url)
        self.queue_list.addItem(item)
        self.url_input.clear()
        self.status_lbl.setStyleSheet("color: rgba(200,200,200,160);")
        self.status_lbl.setText(f"{self.queue_list.count()} URL{'s' if self.queue_list.count() != 1 else ''} queued.")

    def _clear_queue(self):
        self.queue_list.clear()
        self.status_lbl.setStyleSheet("color: rgba(200,200,200,160);")
        self.status_lbl.setText("Queue cleared.")
        self.progress_bar.setValue(0)

    def _start_download(self):
        count = self.queue_list.count()
        if count == 0:
            self.status_lbl.setStyleSheet("color: #ed4245;")
            self.status_lbl.setText("Add at least one URL first.")
            return
        urls = [self.queue_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(count)]
        self.dl_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.thread_spin.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        threads = self.thread_spin.value()
        threading.Thread(target=download_queue, args=(urls, threads), daemon=True).start()

    def _on_queue_item(self, row: int, state: str):
        item = self.queue_list.item(row)
        if item is None:
            return
        if state == "downloading":
            item.setText("▶  " + item.data(Qt.ItemDataRole.UserRole))
            item.setForeground(QColor(180, 140, 255))
        elif state == "done":
            item.setText("✓  " + item.data(Qt.ItemDataRole.UserRole))
            item.setForeground(QColor(87, 242, 135))
        elif state == "failed":
            item.setText("✗  " + item.data(Qt.ItemDataRole.UserRole))
            item.setForeground(QColor(237, 66, 69))

    def _on_progress(self, pct: int, label: str):
        self.status_lbl.setStyleSheet("color: rgba(170,150,255,200);")
        self.status_lbl.setText(label)
        if pct < 0:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(pct)

    def _on_status(self, message: str, color: str):
        self.status_lbl.setStyleSheet(f"color: {color};")
        self.status_lbl.setText(message)

    def _on_finished(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.dl_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.thread_spin.setEnabled(True)


def main():
    handle_update_file()   # exits here if this IS the update file
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    just_updated = cleanup_update_file()
    window = MainWindow(just_updated)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

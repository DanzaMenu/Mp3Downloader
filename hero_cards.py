# Version: 1.0.1

import sys
import os
import json
import time
import subprocess
import urllib.request
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

CURRENT_VERSION = "1.0.1"
GITHUB_API_URL = "https://api.github.com/repos/DanzaMenu/HeroCardsV1.0.0/releases/latest"
SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
UPDATE_FILE = os.path.join(SCRIPT_DIR, "hero_cards_update.py")


def _parse_version(v: str):
    return tuple(int(x) for x in v.lstrip("v").split("."))


# ─── Update logic ────────────────────────────────────────────────────────────

def handle_update_file():
    """If we were launched as _update.py, rename ourselves and relaunch."""
    if SCRIPT_PATH.endswith("hero_cards_update.py"):
        target = os.path.join(SCRIPT_DIR, "hero_cards.py")
        time.sleep(1)
        try:
            os.replace(SCRIPT_PATH, target)
        except Exception as e:
            QMessageBox.critical(None, "Update Error", f"Could not replace file:\n{e}")
            sys.exit(1)
        subprocess.Popen([sys.executable, target])
        sys.exit(0)


def cleanup_update_file():
    """If hero_cards_update.py still exists, we just updated — clean it up."""
    if os.path.exists(UPDATE_FILE):
        try:
            os.remove(UPDATE_FILE)
        except Exception:
            pass
        return True
    return False


def fetch_update_info():
    """Returns (latest_version, download_url) or raises on failure."""
    req = urllib.request.Request(GITHUB_API_URL, headers={"User-Agent": "HeroCards-Updater"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode())
    latest_tag = data.get("tag_name", "").lstrip("v")
    assets = data.get("assets", [])
    dl_url = next(
        (a["browser_download_url"] for a in assets if a["name"] == "hero_cards.py"),
        None
    )
    return latest_tag, dl_url


def download_update(url: str):
    """Downloads the update to hero_cards_update.py."""
    req = urllib.request.Request(url, headers={"User-Agent": "HeroCards-Updater"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(UPDATE_FILE, "wb") as f:
        f.write(data)


# ─── Hero data ───────────────────────────────────────────────────────────────

HEROES = [
    {"name": "Aethon Blaze",  "role": "Warrior",  "hp": 920,  "atk": 310, "def": 280, "rarity": "Legendary"},
    {"name": "Vesper Shade",  "role": "Assassin", "hp": 640,  "atk": 480, "def": 140, "rarity": "Epic"},
    {"name": "Ironhide Rex",  "role": "Tank",     "hp": 1400, "atk": 190, "def": 520, "rarity": "Rare"},
    {"name": "Luna Frost",    "role": "Mage",     "hp": 580,  "atk": 540, "def": 110, "rarity": "Legendary"},
    {"name": "Drek the Bold", "role": "Warrior",  "hp": 870,  "atk": 300, "def": 260, "rarity": "Common"},
    {"name": "Sylvara Wind",  "role": "Ranger",   "hp": 710,  "atk": 410, "def": 180, "rarity": "Epic"},
    {"name": "Colossus Prime","role": "Tank",     "hp": 1600, "atk": 160, "def": 600, "rarity": "Legendary"},
    {"name": "Nixie Spark",   "role": "Mage",     "hp": 520,  "atk": 590, "def": 90,  "rarity": "Rare"},
    {"name": "Grimshaw",      "role": "Assassin", "hp": 600,  "atk": 460, "def": 130, "rarity": "Common"},
    {"name": "Thornback",     "role": "Ranger",   "hp": 760,  "atk": 390, "def": 200, "rarity": "Rare"},
    {"name": "Ember Vox",     "role": "Mage",     "hp": 560,  "atk": 510, "def": 100, "rarity": "Epic"},
    {"name": "Valdris Stone", "role": "Warrior",  "hp": 900,  "atk": 320, "def": 290, "rarity": "Common"},
]

RARITY_COLORS = {
    "Legendary": "#FFD700",
    "Epic":      "#9B59B6",
    "Rare":      "#3498DB",
    "Common":    "#7F8C8D",
}

ROLE_ICONS = {
    "Warrior":  "⚔",
    "Assassin": "🗡",
    "Tank":     "🛡",
    "Mage":     "✨",
    "Ranger":   "🏹",
}


# ─── UI Components ───────────────────────────────────────────────────────────

class HeroCard(QFrame):
    def __init__(self, hero: dict, parent=None):
        super().__init__(parent)
        rarity_color = RARITY_COLORS.get(hero["rarity"], "#7F8C8D")

        self.setFixedSize(200, 270)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1E2535;
                border: 2px solid {rarity_color};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        badge = QLabel(hero["rarity"].upper())
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFont(QFont("Tahoma", 7))
        badge.setStyleSheet(f"""
            color: {rarity_color};
            background-color: rgba(0,0,0,0.4);
            border: 1px solid {rarity_color};
            border-radius: 4px;
            padding: 2px 6px;
        """)
        layout.addWidget(badge)

        avatar = QLabel(ROLE_ICONS.get(hero["role"], "?"))
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(QFont("Segoe UI Emoji", 36))
        avatar.setFixedHeight(80)
        avatar.setStyleSheet("border: none;")
        layout.addWidget(avatar)

        name_lbl = QLabel(hero["name"])
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setFont(QFont("Tahoma", 10))
        name_lbl.setStyleSheet(f"color: {rarity_color}; border: none; font-weight: bold;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        role_lbl = QLabel(hero["role"])
        role_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        role_lbl.setFont(QFont("Tahoma", 8))
        role_lbl.setStyleSheet("color: #AAAAAA; border: none;")
        layout.addWidget(role_lbl)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {rarity_color}; border: none; background: {rarity_color}; max-height: 1px;")
        layout.addWidget(div)

        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(2)
        for label, value, color in [
            ("HP",  hero["hp"],  "#2ECC71"),
            ("ATK", hero["atk"], "#E74C3C"),
            ("DEF", hero["def"], "#3498DB"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(QFont("Tahoma", 8))
            lbl.setStyleSheet(f"color: {color}; border: none; font-weight: bold;")
            val = QLabel(f"{value:,}")
            val.setFont(QFont("Tahoma", 8))
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val.setStyleSheet("color: #FFFFFF; border: none;")
            row.addWidget(lbl)
            row.addWidget(val)
            stats_layout.addLayout(row)

        layout.addLayout(stats_layout)
        layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self, just_updated: bool):
        super().__init__()
        self._just_updated = just_updated
        self.setWindowTitle(f"Hero Cards  |  v{CURRENT_VERSION}  —  Checking for updates...")
        # 1.0.1
        self.setMinimumSize(900, 620)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#12172A"))
        self.setPalette(palette)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #12172A; }")
        scroll.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                background: #1E2535;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #3A4A6A;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        container = QWidget()
        container.setStyleSheet("background: #12172A;")
        grid = QGridLayout(container)
        grid.setContentsMargins(24, 24, 24, 24)
        grid.setSpacing(16)

        cols = 4
        for i, hero in enumerate(HEROES):
            card = HeroCard(hero)
            grid.addWidget(card, i // cols, i % cols)

        scroll.setWidget(container)
        self.setCentralWidget(scroll)

        QTimer.singleShot(500, self._run_update_check)

    def _run_update_check(self):
        if self._just_updated:
            self.setWindowTitle(f"Hero Cards  |  v{CURRENT_VERSION}")
            QMessageBox.information(self, "Updated!", f"Successfully updated to v{CURRENT_VERSION}!")
            return

        self._update_result = None
        self._update_error = None

        def _check():
            try:
                latest, url = fetch_update_info()
                self._update_result = (latest, url)
            except Exception as e:
                self._update_error = str(e)
            QTimer.singleShot(0, self._on_check_complete)

        threading.Thread(target=_check, daemon=True).start()

    def _on_check_complete(self):
        if self._update_error:
            self.setWindowTitle(f"Hero Cards  |  v{CURRENT_VERSION}")
            QMessageBox.warning(self, "Update Check Failed", f"Could not check for updates:\n{self._update_error}")
            return

        latest, url = self._update_result
        if not latest:
            self.setWindowTitle(f"Hero Cards  |  v{CURRENT_VERSION}")
            QMessageBox.information(self, "Up to Date", f"You're up to date! (v{CURRENT_VERSION})")
            return

        if _parse_version(latest) > _parse_version(CURRENT_VERSION):
            self.setWindowTitle(f"Hero Cards  |  v{CURRENT_VERSION}")
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
                    subprocess.Popen([sys.executable, UPDATE_FILE])
                    QApplication.quit()
                except Exception as e:
                    QMessageBox.critical(self, "Update Failed", f"Download failed:\n{e}")
        else:
            self.setWindowTitle(f"Hero Cards  |  v{CURRENT_VERSION}")
            QMessageBox.information(self, "Up to Date", f"You're up to date! (v{CURRENT_VERSION})")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    handle_update_file()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    just_updated = cleanup_update_file()
    window = MainWindow(just_updated)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

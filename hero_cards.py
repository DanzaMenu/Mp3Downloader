# Version: 1.0.0

import sys
import os
import json
import shutil
import subprocess
import urllib.request
import threading
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

CURRENT_VERSION = "1.0.0"
GITHUB_API_URL = "https://api.github.com/repos/DanzaMenu/HeroCardsV1.0.0/releases/latest"
SCRIPT_PATH = os.path.abspath(__file__)


def _parse_version(v: str):
    return tuple(int(x) for x in v.lstrip("v").split("."))


def check_for_update(callback):
    def _check():
        try:
            req = urllib.request.Request(GITHUB_API_URL, headers={"User-Agent": "HeroCards-Updater"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            latest_tag = data.get("tag_name", "").lstrip("v")
            if not latest_tag:
                return
            if _parse_version(latest_tag) > _parse_version(CURRENT_VERSION):
                assets = data.get("assets", [])
                dl_url = next(
                    (a["browser_download_url"] for a in assets if a["name"] == "hero_cards.py"),
                    None
                )
                callback(latest_tag, dl_url)
        except Exception:
            pass
    threading.Thread(target=_check, daemon=True).start()


def perform_update(url: str, new_version: str):
    try:
        backup = SCRIPT_PATH + ".bak"
        shutil.copy2(SCRIPT_PATH, backup)
        req = urllib.request.Request(url, headers={"User-Agent": "HeroCards-Updater"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            new_code = resp.read()
        with open(SCRIPT_PATH, "wb") as f:
            f.write(new_code)
        subprocess.Popen([sys.executable, SCRIPT_PATH])
        QApplication.quit()
    except Exception as e:
        QMessageBox.critical(None, "Update Failed", f"Could not apply update:\n{e}")

HEROES = [
    {"name": "Aethon Blaze", "role": "Warrior", "hp": 920, "atk": 310, "def": 280, "rarity": "Legendary"},
    {"name": "Vesper Shade", "role": "Assassin", "hp": 640, "atk": 480, "def": 140, "rarity": "Epic"},
    {"name": "Ironhide Rex", "role": "Tank", "hp": 1400, "atk": 190, "def": 520, "rarity": "Rare"},
    {"name": "Luna Frost", "role": "Mage", "hp": 580, "atk": 540, "def": 110, "rarity": "Legendary"},
    {"name": "Drek the Bold", "role": "Warrior", "hp": 870, "atk": 300, "def": 260, "rarity": "Common"},
    {"name": "Sylvara Wind", "role": "Ranger", "hp": 710, "atk": 410, "def": 180, "rarity": "Epic"},
    {"name": "Colossus Prime", "role": "Tank", "hp": 1600, "atk": 160, "def": 600, "rarity": "Legendary"},
    {"name": "Nixie Spark", "role": "Mage", "hp": 520, "atk": 590, "def": 90, "rarity": "Rare"},
    {"name": "Grimshaw", "role": "Assassin", "hp": 600, "atk": 460, "def": 130, "rarity": "Common"},
    {"name": "Thornback", "role": "Ranger", "hp": 760, "atk": 390, "def": 200, "rarity": "Rare"},
    {"name": "Ember Vox", "role": "Mage", "hp": 560, "atk": 510, "def": 100, "rarity": "Epic"},
    {"name": "Valdris Stone", "role": "Warrior", "hp": 900, "atk": 320, "def": 290, "rarity": "Common"},
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

        # Rarity badge
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

        # Avatar placeholder
        avatar = QLabel(ROLE_ICONS.get(hero["role"], "?"))
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(QFont("Segoe UI Emoji", 36))
        avatar.setFixedHeight(80)
        avatar.setStyleSheet("border: none;")
        layout.addWidget(avatar)

        # Hero name
        name_lbl = QLabel(hero["name"])
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setFont(QFont("Tahoma", 10))
        name_lbl.setStyleSheet(f"color: {rarity_color}; border: none; font-weight: bold;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        # Role
        role_lbl = QLabel(hero["role"])
        role_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        role_lbl.setFont(QFont("Tahoma", 8))
        role_lbl.setStyleSheet("color: #AAAAAA; border: none;")
        layout.addWidget(role_lbl)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {rarity_color}; border: none; background: {rarity_color}; max-height: 1px;")
        layout.addWidget(div)

        # Stats
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(2)
        for label, value, color in [
            ("HP",  hero["hp"],  "#2ECC71"),
            ("ATK", hero["atk"], "#E74C3C"),
            ("DEF", hero["def"], "#3498DB"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}")
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hero Cards  |  v1.0.0")
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

        QTimer.singleShot(1500, self._start_update_check)

    def _start_update_check(self):
        check_for_update(self._on_update_found)

    def _on_update_found(self, new_version: str, dl_url: str):
        QTimer.singleShot(0, lambda: self._prompt_update(new_version, dl_url))

    def _prompt_update(self, new_version: str, dl_url: str):
        msg = QMessageBox(self)
        msg.setWindowTitle("Update Available")
        msg.setText(f"A new version is available: <b>v{new_version}</b><br>You are on v{CURRENT_VERSION}.<br><br>Update now?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            if dl_url:
                perform_update(dl_url, new_version)
            else:
                QMessageBox.warning(self, "Update Error", "No downloadable asset found for this release.")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

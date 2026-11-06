# Version: 1.0.0

import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette

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


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

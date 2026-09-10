"""
Botão customizado para barra de abas com suporte a contador/badge.
"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class NavTabButton(QPushButton):
    def __init__(self, title: str, count: int = 0, parent: QWidget = None):
        super().__init__(parent)
        self.base_title = title
        self.count = count
        self.setProperty("class", "navTabButton")
        self._update_text()

    def set_count(self, count: int):
        self.count = count
        self._update_text()

    def set_active(self, is_active: bool):
        self.setProperty("active", "true" if is_active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _update_text(self):
        if self.count > 0:
            self.setText(f"{self.base_title}  ({self.count})")
        else:
            self.setText(self.base_title)

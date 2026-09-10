"""
Card visual de tarefa individual no estilo Kanban do Jira.
"""
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...core.models import JiraTaskItem


def _get_initials(name: str) -> str:
    if not name or name.strip().lower() in ("não atribuído", "unassigned", "none"):
        return "?"
    parts = [p for p in name.strip().split() if p]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    elif len(parts) == 1:
        return parts[0][:2].upper()
    return "?"


class KanbanCard(QFrame):
    def __init__(self, task: JiraTaskItem, parent: QWidget = None):
        super().__init__(parent)
        self.task = task
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame#kanbanCard {
                background-color: #22272b;
                border: 1px solid #2d333b;
                border-left: 3px solid #238636;
                border-radius: 4px;
            }
            QFrame#kanbanCard:hover {
                background-color: #282e33;
                border-color: #444c56;
                border-left: 3px solid #2ea043;
            }
        """)
        self.setObjectName("kanbanCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # 1. Título / Resumo da tarefa
        title_label = QLabel(self.task.summary)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #e6edf3; font-size: 12px; font-weight: 500; background: transparent;")
        layout.addWidget(title_label)

        # 2. Linha inferior: Ícone de subtarefa + Código (FF-XXX) + Prioridade + Avatar
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        # Ícone de subtarefa / issue + Chave
        key_box = QHBoxLayout()
        key_box.setSpacing(4)
        subtask_icon = QLabel("⑂")
        subtask_icon.setStyleSheet("color: #a371f7; font-size: 12px; font-weight: bold; background: transparent;")
        key_box.addWidget(subtask_icon)

        key_label = QLabel(self.task.key)
        key_label.setStyleSheet("color: #7d8590; font-size: 11px; font-weight: bold; background: transparent;")
        key_box.addWidget(key_label)
        bottom_layout.addLayout(key_box)

        bottom_layout.addStretch()

        # Ícone de prioridade
        prio_lower = self.task.priority.lower()
        if "highest" in prio_lower or "crític" in prio_lower or "blocker" in prio_lower:
            prio_icon = "▲▲"
            prio_color = "#f85149"
        elif "high" in prio_lower or "alt" in prio_lower:
            prio_icon = "▲"
            prio_color = "#f0883e"
        elif "low" in prio_lower or "baix" in prio_lower:
            prio_icon = "▼"
            prio_color = "#3fb950"
        else:
            prio_icon = "＝"
            prio_color = "#d29922"

        prio_label = QLabel(prio_icon)
        prio_label.setToolTip(f"Prioridade: {self.task.priority}")
        prio_label.setStyleSheet(f"color: {prio_color}; font-size: 12px; font-weight: bold; background: transparent;")
        bottom_layout.addWidget(prio_label)

        # Avatar com iniciais (ex: AJ com fundo verde, igual ao Jira)
        initials = _get_initials(self.task.assignee)
        avatar_label = QLabel(initials)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setFixedSize(20, 20)
        avatar_label.setToolTip(f"Responsável: {self.task.assignee}")

        if initials == "?":
            avatar_style = "background-color: #30363d; color: #8b949e; border-radius: 10px; font-size: 10px; font-weight: bold;"
        else:
            avatar_style = "background-color: #238636; color: #ffffff; border-radius: 10px; font-size: 9px; font-weight: bold;"

        avatar_label.setStyleSheet(avatar_style)
        bottom_layout.addWidget(avatar_label)

        layout.addLayout(bottom_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.task.html_url:
                QDesktopServices.openUrl(QUrl(self.task.html_url))
        super().mousePressEvent(event)


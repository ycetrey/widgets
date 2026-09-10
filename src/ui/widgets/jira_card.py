"""
Card visual representando uma tarefa individual do Jira.
"""
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.models import JiraTaskItem


class JiraCard(QFrame):
    def __init__(self, task: JiraTaskItem, parent: QWidget = None):
        super().__init__(parent)
        self.task = task
        self.setProperty("class", "prCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)

        # 1. Linha Superior: Chave da Issue + Tipo + Status + Prioridade
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        # Chave da issue (ex: DEV-101)
        key_label = QLabel(self.task.key)
        key_label.setStyleSheet(
            "background-color: #3b82f6; color: white; border-radius: 4px; "
            "padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )
        top_layout.addWidget(key_label)

        # Tipo da issue (Bug, História, Tarefa)
        type_label = QLabel(self.task.issue_type)
        type_label.setProperty("class", "tagBadge")
        top_layout.addWidget(type_label)

        top_layout.addStretch()

        # Prioridade com cores
        priority_lower = self.task.priority.lower()
        if "crític" in priority_lower or "highest" in priority_lower or "blocker" in priority_lower:
            prio_color = "#f87171"
            prio_bg = "rgba(239, 68, 68, 0.2)"
            prio_icon = "🔴"
        elif "alt" in priority_lower or "high" in priority_lower:
            prio_color = "#fbbf24"
            prio_bg = "rgba(245, 158, 11, 0.2)"
            prio_icon = "🟠"
        elif "baix" in priority_lower or "low" in priority_lower:
            prio_color = "#34d399"
            prio_bg = "rgba(16, 185, 129, 0.2)"
            prio_icon = "🟢"
        else:
            prio_color = "#60a5fa"
            prio_bg = "rgba(59, 130, 246, 0.2)"
            prio_icon = "🟡"

        prio_label = QLabel(f"{prio_icon} {self.task.priority}")
        prio_label.setStyleSheet(
            f"background-color: {prio_bg}; color: {prio_color}; border-radius: 4px; "
            f"padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )
        top_layout.addWidget(prio_label)

        # Badge do Status
        cat = self.task.status_category.lower()
        if cat == "done" or "conclu" in self.task.status.lower():
            status_style = "background-color: rgba(16, 185, 129, 0.25); color: #34d399; border: 1px solid #10b981;"
        elif cat == "indeterminate" or "andamento" in self.task.status.lower() or "progress" in self.task.status.lower():
            status_style = "background-color: rgba(59, 130, 246, 0.25); color: #60a5fa; border: 1px solid #3b82f6;"
        else:
            status_style = "background-color: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid #64748b;"

        status_label = QLabel(self.task.status)
        status_label.setStyleSheet(f"{status_style} border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
        top_layout.addWidget(status_label)

        main_layout.addLayout(top_layout)

        # 2. Linha Central: Resumo / Título da Tarefa
        title_label = QLabel(self.task.summary)
        title_label.setProperty("class", "prTitle")
        title_label.setWordWrap(True)
        main_layout.addWidget(title_label)

        # 3. Linha Inferior: Atribuído a, Tempo decorrido e Botão para abrir
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)

        assignee_label = QLabel(f"👤 {self.task.assignee}")
        assignee_label.setProperty("class", "prSubtitle")
        bottom_layout.addWidget(assignee_label)

        updated_label = QLabel(f"🕒 Atualizado {self.task.updated_humanized}")
        updated_label.setProperty("class", "prSubtitle")
        bottom_layout.addWidget(updated_label)

        bottom_layout.addStretch()

        open_btn = QPushButton("🔗 Abrir no Jira")
        open_btn.setProperty("class", "actionButton")
        open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        open_btn.clicked.connect(self._open_in_browser)
        bottom_layout.addWidget(open_btn)

        main_layout.addLayout(bottom_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_in_browser()
        super().mousePressEvent(event)

    def _open_in_browser(self):
        if self.task.html_url:
            QDesktopServices.openUrl(QUrl(self.task.html_url))

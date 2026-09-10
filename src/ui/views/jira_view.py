"""
Visualização da aba de Tarefas do Jira.
"""
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.models import JiraTaskItem
from ..widgets.jira_card import JiraCard


class JiraView(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.all_tasks: List[JiraTaskItem] = []
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Barra de Filtros e Ações
        filter_frame = QFrame()
        filter_frame.setObjectName("filterBarFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(10)

        # Seletor de Status
        self.status_combo = QComboBox()
        self.status_combo.addItem("Todos os Status", "all")
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.status_combo)

        # Campo de busca rápida
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filtrar tarefas por código, título...")
        self.search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_input, stretch=1)

        # Botão de Atualizar
        self.refresh_btn = QPushButton("🔄 Atualizar")
        self.refresh_btn.setProperty("class", "actionButton")
        self.refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        filter_layout.addWidget(self.refresh_btn)

        root_layout.addWidget(filter_frame)

        # 2. Banner de Aviso/Erro
        self.error_banner = QFrame()
        self.error_banner.setStyleSheet(
            "background-color: rgba(239, 68, 68, 0.15); border-bottom: 1px solid #ef4444; padding: 6px;"
        )
        self.error_banner_layout = QHBoxLayout(self.error_banner)
        self.error_banner_layout.setContentsMargins(12, 6, 12, 6)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #f87171; font-size: 12px; font-weight: 500;")
        self.error_banner_layout.addWidget(self.error_label)
        self.error_banner.hide()
        root_layout.addWidget(self.error_banner)

        # 3. Área Rolável com a lista de tarefas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(14, 14, 14, 14)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.empty_label = QLabel("Aguardando carregamento de tarefas do Jira...")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
        self.cards_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.cards_container)
        root_layout.addWidget(self.scroll_area, stretch=1)

    def set_error_message(self, message: Optional[str]):
        if message:
            self.error_label.setText(f"⚠️ {message}")
            self.error_banner.show()
        else:
            self.error_banner.hide()

    def set_loading(self, is_loading: bool):
        self.refresh_btn.setEnabled(not is_loading)
        if is_loading:
            self.refresh_btn.setText("⏳ Carregando...")
        else:
            self.refresh_btn.setText("🔄 Atualizar")

    def update_tasks(self, tasks: List[JiraTaskItem]):
        self.all_tasks = tasks

        # Atualiza o combo de status preservando seleção
        current_selection = self.status_combo.currentData()
        statuses = sorted(list(set(t.status for t in self.all_tasks)))

        self.status_combo.blockSignals(True)
        self.status_combo.clear()
        self.status_combo.addItem("Todos os Status", "all")
        for st in statuses:
            count = sum(1 for t in self.all_tasks if t.status == st)
            self.status_combo.addItem(f"{st} ({count})", st)

        idx = self.status_combo.findData(current_selection)
        if idx != -1:
            self.status_combo.setCurrentIndex(idx)
        self.status_combo.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self):
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        selected_status = self.status_combo.currentData()
        query = self.search_input.text().strip().lower()

        filtered = self.all_tasks
        if selected_status and selected_status != "all":
            filtered = [t for t in filtered if t.status == selected_status]

        if query:
            filtered = [
                t for t in filtered
                if (query in t.key.lower() or
                    query in t.summary.lower() or
                    query in t.issue_type.lower() or
                    query in t.priority.lower())
            ]

        if not filtered:
            msg = "🎉 Nenhuma tarefa pendente no Jira!" if not self.all_tasks else "Nenhuma tarefa encontrada para os filtros aplicados."
            lbl = QLabel(msg)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
            self.cards_layout.addWidget(lbl)
        else:
            for task in filtered:
                card = JiraCard(task)
                self.cards_layout.addWidget(card)

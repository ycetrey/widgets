"""
Visualização da aba principal de Pull Requests.
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

from ...core.models import PullRequestItem
from ..widgets.pr_card import PullRequestCard


class PullRequestsView(QWidget):
    refresh_requested = pyqtSignal()
    sort_changed = pyqtSignal(str)

    def __init__(self, sort_order: str = "oldest_first", parent: QWidget = None):
        super().__init__(parent)
        self.all_prs: List[PullRequestItem] = []
        self.current_sort_order = sort_order  # "oldest_first" ou "newest_first"
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Barra de Filtros e Controles
        filter_frame = QFrame()
        filter_frame.setObjectName("filterBarFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(10)

        # Seletor de repositório
        self.repo_combo = QComboBox()
        self.repo_combo.addItem("Todos os Repositórios", "all")
        self.repo_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.repo_combo)

        # Campo de busca
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filtrar por título, autor, #número...")
        self.search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_input, stretch=1)

        # Botão de alternância de ordenação
        self.sort_button = QPushButton()
        self.sort_button.setProperty("class", "actionButton")
        self.sort_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._update_sort_button_label()
        self.sort_button.clicked.connect(self._toggle_sort)
        filter_layout.addWidget(self.sort_button)

        # Botão de Atualizar
        self.refresh_btn = QPushButton("🔄 Atualizar")
        self.refresh_btn.setProperty("class", "actionButton")
        self.refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        filter_layout.addWidget(self.refresh_btn)

        root_layout.addWidget(filter_frame)

        # 2. Faixa de Aviso/Erro (oculta por padrão)
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

        # 3. Área Rolável com a lista de PRs
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(14, 14, 14, 14)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Mensagem de estado vazio ou inicial
        self.empty_label = QLabel("Aguardando carregamento de Pull Requests...")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
        self.cards_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.cards_container)
        root_layout.addWidget(self.scroll_area, stretch=1)

    def _update_sort_button_label(self):
        if self.current_sort_order == "oldest_first":
            self.sort_button.setText("⏳ Mais antigas primeiro")
            self.sort_button.setToolTip("Ordenado da mais antiga para a mais recente. Clique para inverter.")
        else:
            self.sort_button.setText("⚡ Mais recentes primeiro")
            self.sort_button.setToolTip("Ordenado da mais recente para a mais antiga. Clique para inverter.")

    def _toggle_sort(self):
        if self.current_sort_order == "oldest_first":
            self.current_sort_order = "newest_first"
        else:
            self.current_sort_order = "oldest_first"

        self._update_sort_button_label()
        self.sort_changed.emit(self.current_sort_order)
        self._apply_filters()

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

    def update_prs(self, prs: List[PullRequestItem]):
        self.all_prs = prs

        # Atualiza lista de repositórios no ComboBox preservando seleção se possível
        current_selection = self.repo_combo.currentData()
        repos = sorted(list(set(pr.repo for pr in self.all_prs)))

        self.repo_combo.blockSignals(True)
        self.repo_combo.clear()
        self.repo_combo.addItem("Todos os Repositórios", "all")
        for repo in repos:
            repo_count = sum(1 for p in self.all_prs if p.repo == repo)
            self.repo_combo.addItem(f"{repo} ({repo_count})", repo)

        # Restaura seleção
        index = self.repo_combo.findData(current_selection)
        if index != -1:
            self.repo_combo.setCurrentIndex(index)
        self.repo_combo.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self):
        # Limpa cards existentes
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        selected_repo = self.repo_combo.currentData()
        search_query = self.search_input.text().strip().lower()

        # Filtra
        filtered = self.all_prs
        if selected_repo and selected_repo != "all":
            filtered = [pr for pr in filtered if pr.repo == selected_repo]

        if search_query:
            filtered = [
                pr for pr in filtered
                if (search_query in pr.title.lower() or
                    search_query in pr.author.lower() or
                    search_query in f"#{pr.number}" or
                    search_query in pr.repo.lower())
            ]

        # Ordena
        reverse = (self.current_sort_order == "newest_first")
        filtered = sorted(filtered, key=lambda pr: pr.created_at, reverse=reverse)

        # Renderiza cards ou exibe estado vazio
        if not filtered:
            msg = "🎉 Nenhuma Pull Request aberta encontrada!" if not self.all_prs else "Nenhuma PR encontrada para os filtros aplicados."
            lbl = QLabel(msg)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
            self.cards_layout.addWidget(lbl)
        else:
            for pr in filtered:
                card = PullRequestCard(pr)
                self.cards_layout.addWidget(card)

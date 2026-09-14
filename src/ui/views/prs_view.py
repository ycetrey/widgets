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

    def __init__(self, sort_order: str = "oldest_first", current_user: str = "", parent: QWidget = None):
        super().__init__(parent)
        self.all_prs: List[PullRequestItem] = []
        self.current_sort_order = sort_order  # "oldest_first" ou "newest_first"
        self.current_user = current_user.strip() if current_user else ""
        self._init_ui()

    def set_current_user(self, username: str):
        cleaned = username.strip() if username else ""
        if cleaned != self.current_user:
            self.current_user = cleaned
            self._apply_filters()

    def _is_own_pr(self, pr: PullRequestItem) -> bool:
        if not self.current_user:
            return False
        user = self.current_user.lower()
        author = pr.author.lower()
        return author == user

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

        # Seletor de status
        self.status_combo = QComboBox()
        self.status_combo.addItem("Todos os Status", "all")
        self.status_combo.addItem("👀 Aguardando Revisão", "review_required")
        self.status_combo.addItem("✅ Aprovadas", "approved")
        self.status_combo.addItem("🔄 Mudanças Solicitadas", "changes_requested")
        self.status_combo.addItem("📝 Rascunhos", "draft")
        self.status_combo.addItem("🟢 Abertas", "open")
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.status_combo)

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
        self.scroll_area.setObjectName("prsScrollArea")

        self.cards_container = QWidget()
        self.cards_container.setObjectName("cardsContainer")
        self.container_layout = QVBoxLayout(self.cards_container)
        self.container_layout.setContentsMargins(14, 14, 14, 14)
        self.container_layout.setSpacing(0)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Quadro unificado com borda estilo lista do GitHub
        self.prs_frame = QFrame()
        self.prs_frame.setObjectName("prsContainerFrame")
        self.cards_layout = QVBoxLayout(self.prs_frame)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(0)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.container_layout.addWidget(self.prs_frame)

        # Mensagem de estado vazio ou inicial
        self.empty_label = QLabel("Aguardando carregamento de Pull Requests...")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #7d8590; font-size: 14px; padding: 40px;")
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

        # Atualiza lista de status no ComboBox preservando seleção se possível
        current_status_sel = self.status_combo.currentData() or "all"
        self.status_combo.blockSignals(True)
        self.status_combo.clear()

        status_definitions = [
            ("all", "Todos os Status", len(self.all_prs)),
            ("review_required", "👀 Aguardando Revisão", sum(1 for p in self.all_prs if p.status_key == "review_required")),
            ("approved", "✅ Aprovadas", sum(1 for p in self.all_prs if p.status_key == "approved")),
            ("changes_requested", "🔄 Mudanças Solicitadas", sum(1 for p in self.all_prs if p.status_key == "changes_requested")),
            ("draft", "📝 Rascunhos", sum(1 for p in self.all_prs if p.status_key == "draft")),
            ("open", "🟢 Abertas", sum(1 for p in self.all_prs if p.status_key == "open")),
        ]

        for key, label, count in status_definitions:
            self.status_combo.addItem(f"{label} ({count})", key)

        status_idx = self.status_combo.findData(current_status_sel)
        if status_idx != -1:
            self.status_combo.setCurrentIndex(status_idx)
        else:
            self.status_combo.setCurrentIndex(0)
        self.status_combo.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self):
        # Limpa cards existentes
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        selected_repo = self.repo_combo.currentData()
        selected_status = self.status_combo.currentData()
        search_query = self.search_input.text().strip().lower()

        # Filtra
        filtered = self.all_prs
        if selected_repo and selected_repo != "all":
            filtered = [pr for pr in filtered if pr.repo == selected_repo]

        if selected_status and selected_status != "all":
            filtered = [pr for pr in filtered if pr.status_key == selected_status]

        if search_query:
            filtered = [
                pr for pr in filtered
                if (search_query in pr.title.lower() or
                    search_query in pr.author.lower() or
                    search_query in f"#{pr.number}" or
                    search_query in pr.repo.lower() or
                    search_query in pr.status_label.lower())
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
            total_items = len(filtered)
            for i, pr in enumerate(filtered):
                is_own = self._is_own_pr(pr)
                is_last = (i == total_items - 1)
                card = PullRequestCard(pr, is_own_pr=is_own, is_last=is_last)
                self.cards_layout.addWidget(card)

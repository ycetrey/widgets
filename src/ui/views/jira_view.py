"""
Visualização da aba de Tarefas do Jira com suporte a Quadro Kanban e Lista.
"""
from collections import defaultdict
from typing import Dict, List, Optional
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
from ..widgets.kanban_swimlane import KanbanSwimlane


class JiraView(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.all_tasks: List[JiraTaskItem] = []
        self.current_user_name: Optional[str] = None
        self.view_mode = "kanban"  # "kanban" ou "list"
        self._init_ui()

    @staticmethod
    def _is_subtask(t: JiraTaskItem) -> bool:
        if getattr(t, "is_subtask", False):
            return True
        if t.issue_type.lower().startswith("sub"):
            return True
        if t.parent_issue_type and t.parent_issue_type.lower() not in ("epic", "épico", ""):
            return True
        return False

    def set_current_user_name(self, name: Optional[str]):
        self.current_user_name = name

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Barra Superior de Filtros e Ações
        filter_frame = QFrame()
        filter_frame.setObjectName("filterBarFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(8)

        # Alternador de visualização (Kanban vs Lista)
        self.view_toggle_btn = QPushButton("📊 Kanban")
        self.view_toggle_btn.setToolTip("Alternar entre modo Kanban e Lista simples")
        self.view_toggle_btn.setProperty("class", "actionButton")
        self.view_toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.view_toggle_btn.clicked.connect(self._toggle_view_mode)
        filter_layout.addWidget(self.view_toggle_btn)

        # Filtro de Responsável
        self.assignee_combo = QComboBox()
        self.assignee_combo.addItem("👥 Todos", "all")
        self.assignee_combo.addItem("👤 Só Minhas", "mine")
        self.assignee_combo.addItem("❓ Não Atribuídas", "unassigned")
        self.assignee_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.assignee_combo)

        # Filtro de Status
        self.status_combo = QComboBox()
        self.status_combo.addItem("Todos os Status", "all")
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.status_combo)

        # Campo de busca rápida
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filtrar por código ou título...")
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

        # 3. Área Rolável (Suporta scroll vertical e horizontal para as 5 colunas do Kanban)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(14, 14, 14, 14)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.empty_label = QLabel("Aguardando carregamento de tarefas da Sprint do Jira...")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
        self.cards_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.cards_container)
        root_layout.addWidget(self.scroll_area, stretch=1)

    def _toggle_view_mode(self):
        if self.view_mode == "kanban":
            self.view_mode = "list"
            self.view_toggle_btn.setText("📋 Lista")
        else:
            self.view_mode = "kanban"
            self.view_toggle_btn.setText("📊 Kanban")
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

    def update_tasks(self, tasks: List[JiraTaskItem], current_user_name: Optional[str] = None):
        self.all_tasks = tasks
        if current_user_name:
            self.current_user_name = current_user_name

        # Atualiza opções do combo de status preservando seleção
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
        selected_assignee = self.assignee_combo.currentData()
        query = self.search_input.text().strip().lower()

        # Identifica as chaves das histórias/tarefas padrão do usuário carregadas
        user_story_keys = {t.key for t in self.all_tasks if not self._is_subtask(t)}

        # Filtra para que subtarefas de histórias pertencentes a outros usuários (ex: Code Review realizado em história alheia) não sejam listadas
        filtered = [
            t for t in self.all_tasks
            if not self._is_subtask(t) or not t.parent_key or t.parent_key in user_story_keys
        ]

        # Filtro de status
        if selected_status and selected_status != "all":
            filtered = [t for t in filtered if t.status == selected_status]

        # Filtro de responsável
        if selected_assignee == "mine":
            if self.current_user_name:
                user_lower = self.current_user_name.lower()
                filtered = [
                    t for t in filtered
                    if user_lower in t.assignee.lower() or t.assignee.lower() in ("você", "voce")
                ]
            else:
                filtered = [t for t in filtered if t.assignee.lower() not in ("não atribuído", "unassigned", "none", "?")]
        elif selected_assignee == "unassigned":
            filtered = [t for t in filtered if t.assignee.lower() in ("não atribuído", "unassigned", "none", "?")]

        # Filtro textual por chave, resumo, tipo ou pai
        if query:
            filtered = [
                t for t in filtered
                if (query in t.key.lower() or
                    query in t.summary.lower() or
                    query in (t.parent_key or "").lower() or
                    query in (t.parent_summary or "").lower() or
                    query in t.issue_type.lower() or
                    query in t.priority.lower())
            ]

        if not filtered:
            msg = "🎉 Nenhuma tarefa pendente na sprint atual!" if not self.all_tasks else "Nenhuma tarefa encontrada para os filtros aplicados."
            lbl = QLabel(msg)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
            self.cards_layout.addWidget(lbl)
            return

        if self.view_mode == "kanban":
            self._render_kanban_view(filtered)
        else:
            self._render_list_view(filtered)

    def _render_kanban_view(self, tasks: List[JiraTaskItem]):
        # Agrupa por História (Swimlane)
        # No Jira, cada Swimlane representa uma História / Tarefa Padrão.
        # Os cards dentro das colunas do Swimlane são as Subtarefas daquela História.
        # Épicos NÃO são swimlanes: aparecem como badge/tag identificador na História.

        stories: Dict[str, dict] = {}
        story_subtasks: Dict[str, List[JiraTaskItem]] = defaultdict(list)
        standalone_tasks: List[JiraTaskItem] = []

        # 1. Registra todas as Histórias / Tarefas padrão presentes
        for task in tasks:
            if not self._is_subtask(task):
                epic = getattr(task, "epic_summary", None)
                if not epic and task.parent_issue_type and task.parent_issue_type.lower() in ("epic", "épico"):
                    epic = task.parent_summary

                stories[task.key] = {
                    "key": task.key,
                    "summary": task.summary,
                    "status": task.status,
                    "issue_type": task.issue_type,
                    "assignee": task.assignee,
                    "url": task.html_url,
                    "epic": epic,
                    "item": task
                }

        # 2. Agrupa subtarefas por chave da História pai
        for task in tasks:
            if self._is_subtask(task):
                story_key = task.parent_key
                if story_key and story_key in stories:
                    story_subtasks[story_key].append(task)
                elif not story_key:
                    standalone_tasks.append(task)

        # 3. Adiciona subtarefas da subtasks_list da própria história se não tiverem vindo como itens
        for skey, sinfo in list(stories.items()):
            item = sinfo.get("item")
            if item and hasattr(item, "subtasks_list") and item.subtasks_list:
                existing_keys = {st.key for st in story_subtasks[skey]}
                for sub_dict in item.subtasks_list:
                    sub_k = sub_dict.get("key")
                    if sub_k and sub_k not in existing_keys:
                        base_url = item.html_url.rsplit("/browse/", 1)[0] if "/browse/" in item.html_url else ""
                        synthetic_sub = JiraTaskItem(
                            key=sub_k,
                            summary=sub_dict.get("summary", ""),
                            status=sub_dict.get("status", "To Do"),
                            status_category=sub_dict.get("status_category", "new"),
                            priority=sub_dict.get("priority", "Normal"),
                            issue_type=sub_dict.get("issue_type", "Subtarefa"),
                            assignee=sub_dict.get("assignee") or "Não atribuído",
                            created_at=item.created_at,
                            updated_at=item.updated_at,
                            html_url=f"{base_url}/browse/{sub_k}" if base_url else "",
                            assignee_avatar="",
                            parent_key=skey,
                            parent_summary=sinfo["summary"],
                            parent_status=sinfo["status"],
                            parent_issue_type=sinfo["issue_type"],
                            is_subtask=True,
                            epic_key=getattr(item, "epic_key", None),
                            epic_summary=sinfo.get("epic")
                        )
                        story_subtasks[skey].append(synthetic_sub)

        # 4. Renderiza as Swimlanes com subtarefas
        for skey, sinfo in stories.items():
            subs = story_subtasks.get(skey, [])
            if subs:
                swimlane = KanbanSwimlane(
                    parent_key=skey,
                    parent_summary=sinfo["summary"],
                    parent_status=sinfo["status"],
                    parent_url=sinfo["url"],
                    tasks=subs,
                    total_subtasks=len(subs),
                    epic_summary=sinfo.get("epic"),
                    issue_type=sinfo.get("issue_type"),
                    assignee=sinfo.get("assignee"),
                    parent=self.cards_container
                )
                self.cards_layout.addWidget(swimlane)
            else:
                item = sinfo.get("item")
                if item:
                    standalone_tasks.append(item)

        # 5. Renderiza tarefas avulsas (histórias/tarefas sem subtarefas)
        if standalone_tasks:
            standalone_swimlane = KanbanSwimlane(
                parent_key="",
                parent_summary="Tarefas Individuais da Sprint (Sem Subtarefas)",
                parent_status="Ativas",
                parent_url="",
                tasks=standalone_tasks,
                total_subtasks=len(standalone_tasks),
                parent=self.cards_container
            )
            self.cards_layout.addWidget(standalone_swimlane)

    def _render_list_view(self, tasks: List[JiraTaskItem]):
        for task in tasks:
            card = JiraCard(task)
            self.cards_layout.addWidget(card)

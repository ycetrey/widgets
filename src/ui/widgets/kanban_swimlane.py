"""
Swimlane (Raia) do Kanban com agrupamento por Tarefa Pai / História e 5 colunas.
"""
from typing import List, Optional
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.models import JiraTaskItem
from .kanban_card import KanbanCard, _get_initials

KANBAN_COLUMNS = [
    ("A FAZER", ["to do", "a fazer", "open", "aberto", "backlog"]),
    ("EM ANDAMENTO", ["in progress", "em andamento", "em desenvolvimento", "andamento"]),
    ("CODE REVIEW", ["code review", "cr", "em code review", "review"]),
    ("EM HOMOLOGAÇÃO (QA)", ["em homologação (qa)", "em homologação", "homologação", "homologacao", "qa", "testing", "em teste"]),
    ("CONCLUÍDO", ["done", "concluído", "concluido", "resolved", "resolvido", "closed", "finalizado"]),
]


def get_column_index(status: str, status_category: str) -> int:
    s = (status or "").strip().lower()
    for idx, (_, aliases) in enumerate(KANBAN_COLUMNS):
        if any(alias in s for alias in aliases):
            return idx
    cat = (status_category or "").strip().lower()
    if cat == "new":
        return 0
    elif cat == "done":
        return 4
    return 1


class KanbanSwimlane(QWidget):
    def __init__(
        self,
        parent_key: str,
        parent_summary: str,
        parent_status: Optional[str],
        parent_url: str,
        tasks: List[JiraTaskItem],
        total_subtasks: int = 0,
        epic_summary: Optional[str] = None,
        issue_type: Optional[str] = None,
        assignee: Optional[str] = None,
        parent: QWidget = None
    ):
        super().__init__(parent)
        self.parent_key = parent_key
        self.parent_summary = parent_summary
        self.parent_status = parent_status or ""
        self.parent_url = parent_url
        self.tasks = tasks
        self.total_subtasks = total_subtasks if total_subtasks > 0 else len(tasks)
        self.epic_summary = epic_summary
        self.issue_type = issue_type or "Story"
        self.assignee = assignee or (tasks[0].assignee if tasks else "")
        self.is_expanded = True
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 14)
        root_layout.setSpacing(6)

        # 1. Barra de Cabeçalho do Swimlane (Parent / Story)
        self.header_frame = QFrame()
        self.header_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px;
            }
            QFrame:hover {
                background-color: #1c2128;
                border-color: #444c56;
            }
        """)

        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        # Seta de colapso
        self.arrow_label = QLabel("▼")
        self.arrow_label.setStyleSheet("color: #7d8590; font-size: 11px; font-weight: bold; background: transparent;")
        header_layout.addWidget(self.arrow_label)

        # Ícone do Tipo de Issue (História / Bug / Tarefa)
        type_lower = (self.issue_type or "").lower()
        if "bug" in type_lower:
            type_symbol = "●"
            type_bg = "#da3633"
        elif any(k in type_lower for k in ("story", "história", "historia")):
            type_symbol = "☑"
            type_bg = "#1f6feb"
        elif not self.parent_key:
            # Swimlane de tarefas avulsas
            type_symbol = "📋"
            type_bg = "#30363d"
        else:
            type_symbol = "☑"
            type_bg = "#238636"

        type_badge = QLabel(type_symbol)
        type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_badge.setFixedSize(16, 16)
        type_badge.setStyleSheet(f"background-color: {type_bg}; color: white; border-radius: 3px; font-size: 11px; font-weight: bold;")
        type_badge.setToolTip(f"Tipo: {self.issue_type}")
        header_layout.addWidget(type_badge)

        # Chave e Título do Pai / História
        parent_text = f"{self.parent_key}  {self.parent_summary}" if self.parent_key else self.parent_summary
        self.title_label = QLabel(parent_text)
        self.title_label.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: bold; background: transparent;")
        header_layout.addWidget(self.title_label)

        # Contagem de subtarefas: (X subtasks)
        count_label = QLabel(f"({self.total_subtasks} {'subtasks' if self.total_subtasks != 1 else 'subtask'})")
        count_label.setStyleSheet("color: #7d8590; font-size: 12px; background: transparent;")
        header_layout.addWidget(count_label)

        # Badge do Épico (ex: API Integra — Acesso e cobrança)
        if self.epic_summary:
            epic_text = self.epic_summary
            if len(epic_text) > 36:
                epic_text = epic_text[:34] + "..."
            epic_badge = QLabel(epic_text)
            epic_badge.setToolTip(f"Épico: {self.epic_summary}")
            epic_badge.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            """)
            header_layout.addWidget(epic_badge)

        header_layout.addStretch()

        # Badge do Status da História (ex: CODE REVIEW em azul)
        if self.parent_status:
            status_badge = QLabel(self.parent_status)
            status_badge.setStyleSheet("""
                background-color: rgba(56, 139, 253, 0.15);
                color: #58a6ff;
                border: 1px solid #1f6feb;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: bold;
            """)
            header_layout.addWidget(status_badge)

        # Avatar do responsável pela história
        assignee_initials = _get_initials(self.assignee)
        if assignee_initials != "?":
            avatar = QLabel(assignee_initials)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setFixedSize(20, 20)
            avatar.setToolTip(f"Responsável: {self.assignee}")
            avatar.setStyleSheet("background-color: #1f6feb; color: white; border-radius: 10px; font-size: 9px; font-weight: bold;")
            header_layout.addWidget(avatar)

        # Link para abrir pai no navegador
        if self.parent_url:
            open_parent_btn = QPushButton("🔗")
            open_parent_btn.setToolTip(f"Abrir {self.parent_key} no Jira")
            open_parent_btn.setFixedSize(24, 24)
            open_parent_btn.setStyleSheet("background: transparent; border: none; font-size: 12px;")
            open_parent_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            open_parent_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.parent_url)))
            header_layout.addWidget(open_parent_btn)

        root_layout.addWidget(self.header_frame)

        # Permite clicar em qualquer lugar do header para expandir/colapsar
        self.header_frame.mousePressEvent = self._toggle_collapse

        # 2. Container das 5 Colunas
        self.columns_container = QWidget()
        cols_layout = QHBoxLayout(self.columns_container)
        cols_layout.setContentsMargins(0, 4, 0, 4)
        cols_layout.setSpacing(10)

        # Distribui tarefas nas 5 colunas
        column_tasks: List[List[JiraTaskItem]] = [[] for _ in range(5)]
        for t in self.tasks:
            col_idx = get_column_index(t.status, t.status_category)
            column_tasks[col_idx].append(t)

        for idx, (col_name, _) in enumerate(KANBAN_COLUMNS):
            col_frame = self._build_column(col_name, column_tasks[idx], idx)
            cols_layout.addWidget(col_frame)

        root_layout.addWidget(self.columns_container)

    def _build_column(self, col_name: str, tasks: List[JiraTaskItem], col_index: int) -> QFrame:
        col_frame = QFrame()
        col_frame.setStyleSheet("""
            QFrame#kanbanCol {
                background-color: #111418;
                border: 1px solid #21262d;
                border-radius: 6px;
            }
        """)
        col_frame.setObjectName("kanbanCol")
        col_frame.setMinimumWidth(210)

        col_layout = QVBoxLayout(col_frame)
        col_layout.setContentsMargins(8, 8, 8, 8)
        col_layout.setSpacing(8)
        col_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Cabeçalho da coluna: Título + Badge de contagem
        header_box = QHBoxLayout()
        header_box.setContentsMargins(2, 2, 2, 2)
        header_box.setSpacing(6)

        title_lbl = QLabel(col_name)
        title_lbl.setStyleSheet("color: #7d8590; font-size: 11px; font-weight: bold; background: transparent;")
        header_box.addWidget(title_lbl)

        # Badge de contagem (ex: 1/1 ou 2/4)
        count_lbl = QLabel(f"{len(tasks)}")
        count_lbl.setStyleSheet("""
            background-color: #21262d;
            color: #8b949e;
            border-radius: 10px;
            padding: 1px 6px;
            font-size: 10px;
            font-weight: bold;
        """)
        header_box.addWidget(count_lbl)

        if col_name == "CONCLUÍDO":
            check_icon = QLabel("✓✓")
            check_icon.setStyleSheet("color: #2ea043; font-size: 11px; font-weight: bold; background: transparent;")
            header_box.addWidget(check_icon)

        header_box.addStretch()
        col_layout.addLayout(header_box)

        # Cards dentro da coluna
        if tasks:
            for task in tasks:
                card = KanbanCard(task)
                col_layout.addWidget(card)
        else:
            empty_placeholder = QWidget()
            empty_placeholder.setFixedHeight(30)
            col_layout.addWidget(empty_placeholder)

        return col_frame

    def _toggle_collapse(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_expanded = not self.is_expanded
            self.columns_container.setVisible(self.is_expanded)
            self.arrow_label.setText("▼" if self.is_expanded else "▶")


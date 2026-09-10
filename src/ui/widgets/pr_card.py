"""
Card visual representando uma Pull Request individual.
"""
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core.models import PullRequestItem


class PullRequestCard(QFrame):
    def __init__(self, pr: PullRequestItem, parent: QWidget = None):
        super().__init__(parent)
        self.pr = pr
        self.setProperty("class", "prCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)

        # 1. Linha Superior: Repositório + Número da PR + Badge de Urgência/Idade + Draft
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        # Badge do repositório
        repo_label = QLabel(self.pr.repo)
        repo_label.setProperty("class", "repoBadge")
        top_layout.addWidget(repo_label)

        # Número da PR
        num_label = QLabel(f"#{self.pr.number}")
        num_label.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 12px;")
        top_layout.addWidget(num_label)

        if self.pr.is_draft:
            draft_label = QLabel("DRAFT")
            draft_label.setStyleSheet(
                "background-color: #45475a; color: #bac2de; border-radius: 4px; "
                "padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )
            top_layout.addWidget(draft_label)

        top_layout.addStretch()

        # Badge de urgência / idade
        urgency_class_map = {
            "critical": "urgencyCritical",
            "warning": "urgencyWarning",
            "attention": "urgencyAttention",
            "fresh": "urgencyFresh",
        }
        urgency_class = urgency_class_map.get(self.pr.urgency_level, "urgencyFresh")
        age_label = QLabel(f"⏳ {self.pr.age_humanized}")
        age_label.setProperty("class", urgency_class)
        top_layout.addWidget(age_label)

        main_layout.addLayout(top_layout)

        # 2. Linha Central: Título da PR
        title_label = QLabel(self.pr.title)
        title_label.setProperty("class", "prTitle")
        title_label.setWordWrap(True)
        main_layout.addWidget(title_label)

        # 3. Linha de Etiquetas / Labels (se houver)
        if self.pr.labels:
            labels_layout = QHBoxLayout()
            labels_layout.setSpacing(6)
            for label_name in self.pr.labels[:5]:  # Limita a 5 tags para não sobrecarregar
                lbl = QLabel(label_name)
                lbl.setProperty("class", "tagBadge")
                labels_layout.addWidget(lbl)
            labels_layout.addStretch()
            main_layout.addLayout(labels_layout)

        # 4. Linha Inferior: Autor, comentários e botão para abrir
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)

        author_label = QLabel(f"👤 @{self.pr.author}")
        author_label.setProperty("class", "prSubtitle")
        bottom_layout.addWidget(author_label)

        if self.pr.comments_count > 0:
            comm_label = QLabel(f"💬 {self.pr.comments_count}")
            comm_label.setProperty("class", "prSubtitle")
            bottom_layout.addWidget(comm_label)

        bottom_layout.addStretch()

        open_btn = QPushButton("🔗 Abrir no GitHub")
        open_btn.setProperty("class", "actionButton")
        open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        open_btn.clicked.connect(self._open_in_browser)
        bottom_layout.addWidget(open_btn)

        main_layout.addLayout(bottom_layout)

    def mousePressEvent(self, event):
        # Permite abrir clicando em qualquer ponto do card
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_in_browser()
        super().mousePressEvent(event)

    def _open_in_browser(self):
        if self.pr.html_url:
            QDesktopServices.openUrl(QUrl(self.pr.html_url))

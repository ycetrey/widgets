"""
Visualização da coluna de histórico de notificações com suporte a remoção individual e em massa.
"""
from typing import List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.models import NotificationItem
from ..widgets.notification_card import NotificationCard


class NotificationsView(QWidget):
    dismiss_one_requested = pyqtSignal(int)
    clear_all_requested = pyqtSignal()
    update_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.notifications: List[NotificationItem] = []
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Barra Superior de Controle
        header_frame = QFrame()
        header_frame.setObjectName("filterBarFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        self.title_label = QLabel("🔔 Histórico de Notificações")
        self.title_label.setStyleSheet("color: #cdd6f4; font-size: 13px; font-weight: 600;")
        header_layout.addWidget(self.title_label)

        self.count_badge = QLabel("0 itens")
        self.count_badge.setStyleSheet("""
            background-color: #313244;
            color: #a6adc8;
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 500;
        """)
        header_layout.addWidget(self.count_badge)

        header_layout.addStretch()

        # Botão Limpar Tudo
        self.clear_all_btn = QPushButton("🗑️ Limpar tudo")
        self.clear_all_btn.setToolTip("Remover todas as notificações exibidas")
        self.clear_all_btn.setProperty("class", "actionButton")
        self.clear_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clear_all_btn.setEnabled(False)
        self.clear_all_btn.clicked.connect(self.clear_all_requested.emit)
        header_layout.addWidget(self.clear_all_btn)

        root_layout.addWidget(header_frame)

        # 2. Área Rolável com a Coluna de Notificações
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("notificationsScrollArea")

        self.container = QWidget()
        self.container.setObjectName("cardsContainer")
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(14, 14, 14, 14)
        self.cards_layout.setSpacing(6)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Mensagem de estado vazio
        self.empty_label = QLabel("🎉 Nenhuma notificação no momento!\nNovas notificações de Pull Requests e Jira aparecerão aqui.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #7d8590; font-size: 14px; padding: 40px; line-height: 1.5;")
        self.cards_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.container)
        root_layout.addWidget(self.scroll_area, stretch=1)

    def set_notifications(self, notifications: List[NotificationItem]):
        """
        Atualiza a lista de notificações, ordenadas da mais nova para a mais antiga.
        """
        # Garante ordenação decrescente (mais recente primeiro)
        self.notifications = sorted(
            notifications,
            key=lambda n: n.created_at,
            reverse=True
        )

        # Atualiza badge e botão de limpar tudo
        count = len(self.notifications)
        item_text = "1 item" if count == 1 else f"{count} itens"
        self.count_badge.setText(item_text)
        self.clear_all_btn.setEnabled(count > 0)

        # Limpa widgets anteriores
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Renderiza estado vazio ou lista de cards
        if not self.notifications:
            self.empty_label = QLabel("🎉 Nenhuma notificação no momento!\nNovas notificações de Pull Requests e Jira aparecerão aqui.")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet("color: #7d8590; font-size: 14px; padding: 40px; line-height: 1.5;")
            self.cards_layout.addWidget(self.empty_label)
        else:
            total = len(self.notifications)
            for i, notif in enumerate(self.notifications):
                is_last = (i == total - 1)
                card = NotificationCard(notif, is_last=is_last, parent=self.container)
                card.dismiss_clicked.connect(self.dismiss_one_requested.emit)
                card.update_clicked.connect(self.update_requested.emit)
                self.cards_layout.addWidget(card)

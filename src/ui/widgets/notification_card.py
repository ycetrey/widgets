"""
Card visual para exibição individual de notificações com suporte a remoção.
"""
from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.models import NotificationItem


class NotificationCard(QFrame):
    dismiss_clicked = pyqtSignal(int)
    update_clicked = pyqtSignal()

    def __init__(self, notification: NotificationItem, is_last: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self.notification = notification
        self.is_last = is_last
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            NotificationCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                margin-bottom: 6px;
            }
            NotificationCard:hover {
                background-color: #1c2128;
                border-color: #444c56;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. Ícone do Tipo (Esquerda)
        icon_label = QLabel()
        icon_label.setFixedSize(36, 36)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.notification.item_type == "pr":
            icon_label.setText("🔀")
            icon_label.setStyleSheet("""
                background-color: rgba(163, 113, 247, 0.15);
                border: 1px solid rgba(163, 113, 247, 0.4);
                border-radius: 18px;
                font-size: 16px;
            """)
        elif self.notification.item_type == "jira":
            icon_label.setText("📋")
            icon_label.setStyleSheet("""
                background-color: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.4);
                border-radius: 18px;
                font-size: 16px;
            """)
        elif self.notification.item_type == "update":
            icon_label.setText("🚀")
            icon_label.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.15);
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 18px;
                font-size: 16px;
            """)
        else:
            icon_label.setText("🔔")
            icon_label.setStyleSheet("""
                background-color: rgba(245, 158, 11, 0.15);
                border: 1px solid rgba(245, 158, 11, 0.4);
                border-radius: 18px;
                font-size: 16px;
            """)

        main_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        # 2. Conteúdo Central (Título, Tempo, Mensagem e Link Opcional)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        # Topo do conteúdo: Título + Tempo
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        title_lbl = QLabel(self.notification.title)
        title_lbl.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: 600;")
        top_layout.addWidget(title_lbl)

        time_lbl = QLabel(self.notification.time_humanized)
        time_lbl.setStyleSheet("color: #7d8590; font-size: 11px;")
        top_layout.addWidget(time_lbl)

        top_layout.addStretch()
        content_layout.addLayout(top_layout)

        # Mensagem da notificação
        msg_lbl = QLabel(self.notification.message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #a6adc8; font-size: 12px; line-height: 1.3;")
        content_layout.addWidget(msg_lbl)

        # Ações específicas por tipo
        if self.notification.item_type == "update":
            action_layout = QHBoxLayout()
            action_layout.setSpacing(6)
            update_btn = QPushButton("🔄 Atualizar e Reiniciar")
            update_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            update_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            update_btn.clicked.connect(self.update_clicked.emit)
            action_layout.addWidget(update_btn)
            action_layout.addStretch()
            content_layout.addLayout(action_layout)
        elif self.notification.link_url:
            link_layout = QHBoxLayout()
            link_layout.setSpacing(6)

            open_btn = QPushButton("🔗 Abrir no navegador")
            open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #58a6ff;
                    border: none;
                    font-size: 11px;
                    text-align: left;
                    padding: 2px 0px;
                }
                QPushButton:hover {
                    color: #79b8ff;
                    text-decoration: underline;
                }
            """)
            open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.notification.link_url)))
            link_layout.addWidget(open_btn)
            link_layout.addStretch()
            content_layout.addLayout(link_layout)

        main_layout.addLayout(content_layout, stretch=1)

        # 3. Botão de Remover Notificação (Direita)
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setToolTip("Remover notificação")
        dismiss_btn.setFixedSize(26, 26)
        dismiss_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #7d8590;
                border: 1px solid transparent;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                border-color: rgba(239, 68, 68, 0.4);
                color: #f87171;
            }
        """)
        dismiss_btn.clicked.connect(lambda: self.dismiss_clicked.emit(self.notification.id))
        main_layout.addWidget(dismiss_btn, 0, Qt.AlignmentFlag.AlignTop)

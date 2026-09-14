"""
Banner visual de notificação de atualização exibido no topo da janela principal.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ...core.updater import UpdateInfo


class UpdateBannerWidget(QFrame):
    update_requested = pyqtSignal()
    details_requested = pyqtSignal()
    dismiss_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.update_info: UpdateInfo = None
        self._init_ui()
        self.setVisible(False)

    def _init_ui(self):
        self.setObjectName("updateBanner")
        self.setStyleSheet("""
            QFrame#updateBanner {
                background-color: #1e2030;
                border-bottom: 2px solid #3b82f6;
                padding: 6px 14px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Ícone do foguete
        icon_lbl = QLabel("🚀")
        icon_lbl.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_lbl)

        # Texto descritivo
        self.msg_lbl = QLabel("Nova versão disponível no GitHub!")
        self.msg_lbl.setStyleSheet("color: #cdd6f4; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.msg_lbl)

        layout.addStretch()

        # Botão Ver Novidades
        self.details_btn = QPushButton("ℹ️ Novidades")
        self.details_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.details_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #45475a;
                color: #ffffff;
            }
        """)
        self.details_btn.clicked.connect(self.details_requested.emit)
        layout.addWidget(self.details_btn)

        # Botão Atualizar e Reiniciar
        self.update_btn = QPushButton("🔄 Atualizar e Reiniciar")
        self.update_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        self.update_btn.clicked.connect(self.update_requested.emit)
        layout.addWidget(self.update_btn)

        # Botão Fechar Banner
        self.dismiss_btn = QPushButton("✕")
        self.dismiss_btn.setToolTip("Ocultar aviso")
        self.dismiss_btn.setFixedSize(24, 24)
        self.dismiss_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #a6adc8;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f38ba8;
            }
        """)
        self.dismiss_btn.clicked.connect(self._dismiss)
        layout.addWidget(self.dismiss_btn)

    def show_update(self, info: UpdateInfo):
        self.update_info = info
        commits_str = f"{info.commits_behind} novo(s) commit(s)" if info.commits_behind > 0 else "novos commits"
        self.msg_lbl.setText(
            f"<b>Nova versão disponível!</b> Há {commits_str} no GitHub (branch: <code>{info.branch}</code>)."
        )
        self.setVisible(True)

    def _dismiss(self):
        self.setVisible(False)
        self.dismiss_requested.emit()

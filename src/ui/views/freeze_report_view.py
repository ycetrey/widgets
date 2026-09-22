"""
Visualização da aba de Relatórios de Sprint Freeze.
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

from ...core.models import SprintFreezeReport
from ..widgets.freeze_report_card import FreezeReportCard


class FreezeReportView(QWidget):
    generate_requested = pyqtSignal()
    download_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.reports: List[SprintFreezeReport] = []
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header_frame = QFrame()
        header_frame.setObjectName("filterBarFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        self.title_label = QLabel("🧊 Relatórios de Sprint Freeze (escopo: consulta JQL configurada)")
        self.title_label.setStyleSheet("color: #cdd6f4; font-size: 13px; font-weight: 600;")
        header_layout.addWidget(self.title_label)

        self.status_label = QLabel("Nenhum relatório gerado ainda.")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        self.generate_btn = QPushButton("🧊 Gerar Relatório Agora")
        self.generate_btn.setProperty("class", "primaryButton")
        self.generate_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.generate_btn.clicked.connect(self.generate_requested.emit)
        header_layout.addWidget(self.generate_btn)

        root_layout.addWidget(header_frame)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(14, 14, 14, 14)
        self.cards_layout.setSpacing(6)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.empty_label = QLabel(
            "Nenhum relatório gerado ainda.\nClique em \"Gerar Relatório Agora\" para criar o primeiro."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #7d8590; font-size: 14px; padding: 40px; line-height: 1.5;")
        self.cards_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.container)
        root_layout.addWidget(self.scroll_area, stretch=1)

    def set_reports(self, reports: List[SprintFreezeReport]):
        self.reports = reports

        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not reports:
            self.empty_label = QLabel(
                "Nenhum relatório gerado ainda.\nClique em \"Gerar Relatório Agora\" para criar o primeiro."
            )
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet("color: #7d8590; font-size: 14px; padding: 40px; line-height: 1.5;")
            self.cards_layout.addWidget(self.empty_label)
            self.status_label.setText("Nenhum relatório gerado ainda.")
        else:
            for report in reports:
                card = FreezeReportCard(report, parent=self.container)
                card.download_clicked.connect(self.download_requested.emit)
                self.cards_layout.addWidget(card)
            last = reports[0]
            self.status_label.setText(
                f"Última geração: {last.generated_at.astimezone().strftime('%d/%m/%Y %H:%M')} — "
                f"{last.promoted_count} promovidas / {last.retained_count} retidas"
            )

    def set_generating(self, generating: bool):
        self.generate_btn.setEnabled(not generating)
        self.generate_btn.setText("⏳ Gerando..." if generating else "🧊 Gerar Relatório Agora")

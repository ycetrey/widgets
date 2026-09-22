"""
Card visual para exibição de um relatório de Sprint Freeze já gerado.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.models import SprintFreezeReport


class FreezeReportCard(QFrame):
    download_clicked = pyqtSignal(str)

    def __init__(self, report: SprintFreezeReport, parent: QWidget = None):
        super().__init__(parent)
        self.report = report
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            FreezeReportCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                margin-bottom: 6px;
            }
            FreezeReportCard:hover {
                background-color: #1c2128;
                border-color: #444c56;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(12)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        date_str = self.report.generated_at.astimezone().strftime("%d/%m/%Y %H:%M")
        origin = "🤖 Automático" if self.report.is_automatic else "🖱️ Manual"

        title_lbl = QLabel(f"🧊 {self.report.sprint_name} — {date_str} ({origin})")
        title_lbl.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: 600;")
        content_layout.addWidget(title_lbl)

        self.summary_label = QLabel(
            f"{self.report.promoted_count} promovidas / {self.report.retained_count} retidas "
            f"de {self.report.total_tasks} tarefas"
        )
        self.summary_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        content_layout.addWidget(self.summary_label)

        main_layout.addLayout(content_layout, stretch=1)

        self.download_btn = QPushButton("⬇️ Baixar PDF")
        self.download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.download_btn.setProperty("class", "actionButton")
        self.download_btn.clicked.connect(lambda: self.download_clicked.emit(self.report.pdf_path))
        main_layout.addWidget(self.download_btn, 0, Qt.AlignmentFlag.AlignVCenter)

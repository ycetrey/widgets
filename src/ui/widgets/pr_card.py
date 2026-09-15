"""
Card visual representando uma Pull Request individual no estilo GitHub List Row.
"""
from typing import Optional
from PyQt6.QtCore import QByteArray, QSize, QUrl, Qt
from PyQt6.QtGui import QColor, QCursor, QDesktopServices, QPainter, QPixmap

try:
    from PyQt6.QtSvg import QSvgRenderer
    HAS_SVG = True
except ImportError:
    QSvgRenderer = None
    HAS_SVG = False

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core.models import PullRequestItem

PR_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path fill="{color}" d="M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"/></svg>"""

COMMENT_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path fill="{color}" d="M1 2.75C1 1.784 1.784 1 2.75 1h10.5c.966 0 1.75.784 1.75 1.75v7.5A1.75 1.75 0 0 1 13.25 12H9.06l-2.573 2.573A1.458 1.458 0 0 1 4 13.543V12H2.75A1.75 1.75 0 0 1 1 10.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h2a.75.75 0 0 1 .75.75v2.19l2.72-2.72a.749.749 0 0 1 .53-.22h4.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"/></svg>"""

_PIXMAP_CACHE = {}


def _render_svg_pixmap(svg_template: str, color: str, size: int = 16) -> QPixmap:
    key = (svg_template, color, size)
    if key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]

    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    if HAS_SVG and QSvgRenderer is not None:
        svg_str = svg_template.format(color=color)
        renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
    else:
        # Fallback elegante caso PyQt6.QtSvg não esteja disponível no ambiente
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        q_color = QColor(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(q_color)
        if "M1.5 3.25" in svg_template:
            # PR Icon: nós simplificados
            painter.drawEllipse(3, 2, 4, 4)
            painter.drawEllipse(3, 10, 4, 4)
            painter.drawEllipse(9, 7, 4, 4)
            painter.setPen(q_color)
            painter.drawLine(5, 6, 5, 10)
            painter.drawLine(5, 6, 9, 7)
        else:
            # Comment Icon: balão simplificado
            painter.drawRoundedRect(2, 3, 12, 9, 2, 2)
        painter.end()

    _PIXMAP_CACHE[key] = pixmap
    return pixmap


class PullRequestCard(QFrame):
    def __init__(self, pr: PullRequestItem, is_own_pr: bool = False, is_last: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self.pr = pr
        self.is_own_pr = is_own_pr
        self.is_last = is_last
        self.setProperty("class", "prRow")
        self.setProperty("isOwn", "true" if is_own_pr else "false")
        self.setProperty("isLast", "true" if is_last else "false")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(f"Abrir PR #{self.pr.number} no GitHub\n{self.pr.html_url}")
        self.setFixedHeight(67)
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 11, 16, 11)
        main_layout.setSpacing(12)

        # 1. Ícone da PR à esquerda (Verde se aberta, Cinza se draft)
        icon_color = "#7d8590" if self.pr.is_draft else "#3fb950"
        pr_pixmap = _render_svg_pixmap(PR_ICON_SVG, icon_color, 16)

        icon_label = QLabel()
        icon_label.setPixmap(pr_pixmap)
        icon_label.setFixedSize(16, 16)

        icon_wrapper = QVBoxLayout()
        icon_wrapper.setContentsMargins(0, 2, 0, 0)
        icon_wrapper.setSpacing(0)
        icon_wrapper.addWidget(icon_label)
        icon_wrapper.addStretch()
        main_layout.addLayout(icon_wrapper)

        # 2. Conteúdo Central: Linha 1 (Título + Badge azul do repo) e Linha 2 (Metadados)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Linha 1: Título + Badge azul do repositório
        top_line = QHBoxLayout()
        top_line.setContentsMargins(0, 0, 0, 0)
        top_line.setSpacing(8)

        title_label = QLabel(self.pr.title)
        title_label.setProperty("class", "prTitle")
        title_label.setStyleSheet("color: #e6edf3; font-weight: 600; font-size: 14px;")
        title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_line.addWidget(title_label)

        # Badgezinho azul discreto com o repositório
        repo_badge = QLabel(self.pr.repo)
        repo_badge.setProperty("class", "repoBadgeBlue")
        repo_badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        top_line.addWidget(repo_badge)

        top_line.addStretch()
        content_layout.addLayout(top_line)

        # Linha 2: Metadados estilo GitHub: #num · autor opened X ago · Updated Y ago · Review · Checks
        meta_parts = []

        # #Número
        meta_parts.append(f'<span style="color: #7d8590;">#{self.pr.number}</span>')

        # autor opened há X tempo
        opened_time = self.pr.opened_humanized
        meta_parts.append(f'<span style="color: #7d8590;">{self.pr.author} opened {opened_time}</span>')

        # Updated há Y tempo
        if self.pr.updated_at:
            updated_time = self.pr.updated_humanized
            if updated_time:
                meta_parts.append(f'<span style="color: #7d8590;">Updated {updated_time}</span>')

        # Status de Revisão (ex: ➖ Review required, ✔ Approved, ❌ Changes requested)
        rev = self.pr.review_display_github
        if rev:
            rev_text, rev_color, rev_icon = rev
            meta_parts.append(f'<span style="color: {rev_color}; font-weight: 500;">{rev_icon} {rev_text}</span>')

        # Status de CI / Checks (ex: ✔ 5/5, ❌ 4/5)
        if self.pr.checks_summary:
            state = (self.pr.checks_state or "").upper()
            is_success = (state == "SUCCESS")
            is_failure = (state == "FAILURE")

            # Se não veio state explícito, deduz pela fração 5/5 vs 4/5
            if not is_success and not is_failure and "/" in self.pr.checks_summary:
                parts = self.pr.checks_summary.split("/")
                if len(parts) == 2 and parts[0] == parts[1]:
                    is_success = True
                else:
                    is_failure = True

            if is_success:
                meta_parts.append(f'<span style="color: #3fb950; font-weight: 500;">✔ {self.pr.checks_summary}</span>')
            elif is_failure:
                meta_parts.append(f'<span style="color: #f85149; font-weight: 500;">❌ {self.pr.checks_summary}</span>')
            else:
                meta_parts.append(f'<span style="color: #d29922; font-weight: 500;">🟡 {self.pr.checks_summary}</span>')

        dot_sep = ' <span style="color: #7d8590;">·</span> '
        meta_label = QLabel(dot_sep.join(meta_parts))
        meta_label.setProperty("class", "prMeta")
        meta_label.setTextFormat(Qt.TextFormat.RichText)
        content_layout.addWidget(meta_label)

        main_layout.addLayout(content_layout, stretch=1)

        # 3. Contador de Comentários no canto direito (se houver comentários)
        if self.pr.comments_count > 0:
            comm_container = QWidget()
            comm_layout = QHBoxLayout(comm_container)
            comm_layout.setContentsMargins(0, 0, 0, 0)
            comm_layout.setSpacing(5)

            comm_icon = QLabel()
            comm_icon.setPixmap(_render_svg_pixmap(COMMENT_ICON_SVG, "#7d8590", 16))
            comm_icon.setFixedSize(16, 16)
            comm_layout.addWidget(comm_icon)

            comm_count_label = QLabel(str(self.pr.comments_count))
            comm_count_label.setProperty("class", "commentCount")
            comm_layout.addWidget(comm_count_label)

            main_layout.addWidget(comm_container, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_in_browser()
        super().mousePressEvent(event)

    def _open_in_browser(self):
        if self.pr.html_url:
            QDesktopServices.openUrl(QUrl(self.pr.html_url))

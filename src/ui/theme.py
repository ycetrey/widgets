"""
Temas e estilos visuais inspirados no GNOME / Adwaita Dark.
"""

DARK_THEME_QSS = """
/* Estilo Geral */
QMainWindow, QWidget#centralWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Cantarell', 'Segoe UI', 'DejaVu Sans', Ubuntu, sans-serif;
    font-size: 13px;
}

/* Barra Superior de Abas */
QFrame#tabBarFrame {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    padding: 6px 12px;
}

QPushButton.navTabButton {
    background-color: transparent;
    color: #a6adc8;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    text-align: center;
}

QPushButton.navTabButton:hover {
    background-color: #313244;
    color: #cdd6f4;
}

QPushButton.navTabButton[active="true"] {
    background-color: #3b82f6;
    color: #ffffff;
}

/* Barra de Filtros e Ações */
QFrame#filterBarFrame {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    padding: 8px 14px;
}

QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #89b4fa;
    background-color: #363a4f;
}

QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 140px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left-width: 0px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
}

/* Botões de Ação */
QPushButton.actionButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}

QPushButton.actionButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}

QPushButton.primaryButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}

QPushButton.primaryButton:hover {
    background-color: #2563eb;
}

/* Container de Lista de Pull Requests (Estilo GitHub) */
QFrame#prsContainerFrame {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
}

/* Linha de Pull Request individual (GitHub List Row) */
QFrame.prRow, QFrame[class="prRow"] {
    background-color: #161b22;
    border: none;
    border-bottom: 1px solid #30363d;
    border-left: 3px solid transparent;
    padding: 0px;
    max-height: 67px;
    min-height: 67px;
}

QFrame.prCard, QFrame[class="prCard"] {
    background-color: #161b22;
    border: none;
    border-bottom: 1px solid #30363d;
    border-left: 3px solid transparent;
    padding: 10px 14px;
}

QFrame.prRow:hover, QFrame[class="prRow"]:hover, QFrame.prCard:hover {
    background-color: #1c2128;
    border-left: 3px solid #1f6feb;
}

/* Borda azul na esquerda para PRs do próprio usuário */
QFrame.prRow[isOwn="true"], QFrame[class="prRow"][isOwn="true"], QFrame.prCard[isOwn="true"] {
    border-left: 3px solid #1f6feb;
}

QFrame.prRow[isOwn="true"]:hover, QFrame[class="prRow"][isOwn="true"]:hover, QFrame.prCard[isOwn="true"]:hover {
    background-color: #1c2128;
    border-left: 3px solid #388bfd;
}

/* Último item sem borda inferior dupla */
QFrame.prRow[isLast="true"], QFrame[class="prRow"][isLast="true"] {
    border-bottom: none;
}

QLabel.prTitle {
    color: #e6edf3;
    font-size: 14px;
    font-weight: 600;
}

QLabel.prTitle:hover {
    color: #58a6ff;
    text-decoration: underline;
}

QLabel.prMeta {
    color: #7d8590;
    font-size: 12px;
}

/* Badge azul sutil de repositório */
QLabel.repoBadgeBlue {
    background-color: rgba(56, 139, 253, 0.12);
    color: #58a6ff;
    border: 1px solid rgba(56, 139, 253, 0.35);
    border-radius: 10px;
    padding: 1px 7px;
    font-size: 11px;
    font-weight: 500;
}

QLabel.commentCount {
    color: #7d8590;
    font-size: 12px;
    font-weight: 500;
}

QLabel.prSubtitle {
    color: #7d8590;
    font-size: 12px;
}

QLabel.repoBadge {
    background-color: #313244;
    color: #89b4fa;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.tagBadge {
    background-color: #363a4f;
    color: #b4befe;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
}

/* Badges de Status da PR */
QLabel.statusReviewRequired {
    background-color: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    border: 1px solid #f59e0b;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.statusApproved {
    background-color: rgba(16, 185, 129, 0.2);
    color: #34d399;
    border: 1px solid #10b981;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.statusChangesRequested {
    background-color: rgba(239, 68, 68, 0.2);
    color: #f87171;
    border: 1px solid #ef4444;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.statusDraft {
    background-color: #313244;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.statusOpen {
    background-color: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    border: 1px solid #3b82f6;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 500;
}

/* Badges de Urgência por Idade da PR */
QLabel.urgencyCritical {
    background-color: rgba(239, 68, 68, 0.2);
    color: #f87171;
    border: 1px solid #ef4444;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.urgencyWarning {
    background-color: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    border: 1px solid #f59e0b;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.urgencyAttention {
    background-color: rgba(59, 130, 246, 0.2);
    color: #60a5fa;
    border: 1px solid #3b82f6;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.urgencyFresh {
    background-color: rgba(16, 185, 129, 0.2);
    color: #34d399;
    border: 1px solid #10b981;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

/* Barra de Rolagem e Áreas de Conteúdo */
QScrollArea, QWidget#cardsContainer {
    border: none;
    background-color: #0d1117;
}

QScrollBar:vertical {
    background-color: #181825;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Barra de Status Inferior */
QStatusBar {
    background-color: #11111b;
    color: #a6adc8;
    font-size: 11px;
    border-top: 1px solid #313244;
}
"""


def apply_theme(app, dark_mode: bool = True):
    if dark_mode:
        app.setStyleSheet(DARK_THEME_QSS)
    else:
        app.setStyleSheet("")

"""
Gerenciador do Ícone de Bandeja do Sistema (System Tray).
"""
import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


class SystemTrayManager(QSystemTrayIcon):
    toggle_window_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    update_requested = pyqtSignal()

    def __init__(self, icon_path: str, parent: QWidget = None):
        super().__init__(parent)
        self.icon_path = icon_path

        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
        else:
            print(f"[Tray] Ícone não encontrado no caminho: {icon_path}")

        self.setToolTip("Dev Status Widget - Monitor de Pull Requests")
        self._create_menu()
        self.activated.connect(self._on_activated)

    def _create_menu(self):
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; padding: 4px; } "
            "QMenu::item { padding: 6px 20px; border-radius: 4px; } "
            "QMenu::item:selected { background-color: #3b82f6; color: white; }"
        )

        self.update_action = QAction("🚀 Atualização Disponível", self)
        self.update_action.triggered.connect(self.update_requested.emit)
        self.update_action.setVisible(False)
        menu.addAction(self.update_action)
        self.update_separator = menu.addSeparator()
        self.update_separator.setVisible(False)

        show_action = QAction("🪟 Mostrar / Ocultar Janela", self)
        show_action.triggered.connect(self.toggle_window_requested.emit)
        menu.addAction(show_action)

        refresh_action = QAction("🔄 Atualizar Agora", self)
        refresh_action.triggered.connect(self.refresh_requested.emit)
        menu.addAction(refresh_action)

        settings_action = QAction("⚙️ Configurações", self)
        settings_action.triggered.connect(self.open_settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("❌ Sair", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def set_update_available(self, available: bool, commit_count: int = 0):
        """Exibe ou oculta a ação de atualização no menu de contexto da bandeja."""
        if available:
            commits_str = f"({commit_count} novo{'s' if commit_count > 1 else ''})" if commit_count > 0 else ""
            self.update_action.setText(f"🚀 Atualizar Widget {commits_str}".strip())
            self.update_action.setVisible(True)
            self.update_separator.setVisible(True)
        else:
            self.update_action.setVisible(False)
            self.update_separator.setVisible(False)

    def _on_activated(self, reason):
        # Clique com o botão esquerdo ou duplo clique alterna visibilidade da janela
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_window_requested.emit()

    def update_tooltip(self, pr_count: int):
        if pr_count == 1:
            self.setToolTip("Dev Status Widget - 1 PR aberta")
        else:
            self.setToolTip(f"Dev Status Widget - {pr_count} PRs abertas")

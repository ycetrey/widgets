"""
Janela principal do aplicativo com suporte a abas, bandeja e auto-refresh.
"""
import os
from datetime import datetime
from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core.config import ConfigManager
from ..core.models import AppConfig
from ..core.notifier import DesktopNotifier
from ..providers.github_provider import GitHubProvider
from ..providers.jira_provider import JiraProvider
from .tray import SystemTrayManager
from .views.jira_view import JiraView
from .views.prs_view import PullRequestsView
from .views.settings_view import SettingsView
from .widgets.tab_button import NavTabButton


class FetchWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, github_provider: GitHubProvider, jira_provider: JiraProvider = None):
        super().__init__()
        self.github_provider = github_provider
        self.jira_provider = jira_provider

    def run(self):
        pr_result = self.github_provider.fetch() if self.github_provider else {"items": [], "new_items": [], "errors": []}
        jira_result = self.jira_provider.fetch() if self.jira_provider else {"items": [], "new_items": [], "errors": []}
        self.finished.emit({
            "prs": pr_result,
            "jira": jira_result
        })


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager, icon_path: str, provider=None, jira_provider=None):
        super().__init__()
        self.config_manager = config_manager
        self.config: AppConfig = config_manager.config
        self.icon_path = icon_path

        # Inicializa o provedor GitHub (padrão GitHub ou customizado/mock)
        if provider is not None:
            self.github_provider = provider
        else:
            self.github_provider = GitHubProvider(
                token=self.config.github_token,
                repositories=self.config.repositories,
                sort_order=self.config.sort_order
            )

        # Inicializa o provedor Jira
        if jira_provider is not None:
            self.jira_provider = jira_provider
        else:
            self.jira_provider = JiraProvider(
                jira_url=self.config.jira_url,
                email=self.config.jira_email,
                api_token=self.config.jira_api_token,
                jql=self.config.jira_jql,
                demo_mode=False
            )

        self.notifier = DesktopNotifier(icon_path=self.icon_path)

        # Worker e Thread
        self.thread: QThread = None
        self.worker: FetchWorker = None
        self.is_fetching = False

        # Timer de auto-refresh
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.start_fetch)

        # Tray
        self.tray = SystemTrayManager(icon_path=self.icon_path, parent=self)
        self.notifier.set_tray_icon(self.tray)

        self._init_ui()
        self._setup_tray_connections()
        self._setup_shortcuts()
        self._start_timer()

        # Dispara primeira busca imediatamente
        self.start_fetch()

    def _init_ui(self):
        self.setWindowTitle("Dev Status Widget - Monitor de PRs e Jira")
        self.resize(780, 700)
        self.setMinimumSize(560, 500)

        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Barra Superior com Abas / Botões
        tab_frame = QFrame()
        tab_frame.setObjectName("tabBarFrame")
        tab_layout = QHBoxLayout(tab_frame)
        tab_layout.setContentsMargins(12, 6, 12, 6)
        tab_layout.setSpacing(8)

        # Aba 0: Pull Requests
        self.tab_prs = NavTabButton("🔀 Pull Requests", count=0)
        self.tab_prs.set_active(True)
        self.tab_prs.clicked.connect(lambda: self._switch_tab(0))
        tab_layout.addWidget(self.tab_prs)

        # Aba 1: Jira Tarefas
        self.tab_jira = NavTabButton("📋 Jira Tarefas", count=0)
        self.tab_jira.set_active(False)
        self.tab_jira.clicked.connect(lambda: self._switch_tab(1))
        tab_layout.addWidget(self.tab_jira)

        # Aba 2: Configurações
        self.tab_settings = NavTabButton("⚙️ Configurações", count=0)
        self.tab_settings.set_active(False)
        self.tab_settings.clicked.connect(lambda: self._switch_tab(2))
        tab_layout.addWidget(self.tab_settings)

        tab_layout.addStretch()
        main_layout.addWidget(tab_frame)

        # 2. Pilha de Visualizações (StackedWidget)
        self.stack = QStackedWidget()

        # View 0: Pull Requests
        self.prs_view = PullRequestsView(sort_order=self.config.sort_order)
        self.prs_view.refresh_requested.connect(self.start_fetch)
        self.prs_view.sort_changed.connect(self._on_sort_changed)
        self.stack.addWidget(self.prs_view)

        # View 1: Jira Tarefas
        self.jira_view = JiraView()
        self.jira_view.refresh_requested.connect(self.start_fetch)
        self.stack.addWidget(self.jira_view)

        # View 2: Configurações
        self.settings_view = SettingsView(config=self.config)
        self.settings_view.settings_saved.connect(self._on_settings_saved)
        self.settings_view.test_notification_requested.connect(self._on_test_notification)
        self.stack.addWidget(self.settings_view)

        main_layout.addWidget(self.stack, stretch=1)

        # 3. Barra de Status Inferior
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto")

    def _setup_tray_connections(self):
        self.tray.show()
        self.tray.toggle_window_requested.connect(self.toggle_window_visibility)
        self.tray.refresh_requested.connect(self.start_fetch)
        self.tray.open_settings_requested.connect(lambda: self._switch_tab(2))
        self.tray.quit_requested.connect(self.quit_app)

    def _setup_shortcuts(self):
        refresh_f5 = QShortcut(QKeySequence("F5"), self)
        refresh_f5.activated.connect(self.start_fetch)

        refresh_ctrl_r = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_ctrl_r.activated.connect(self.start_fetch)

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.tab_prs.set_active(index == 0)
        self.tab_jira.set_active(index == 1)
        self.tab_settings.set_active(index == 2)

    def _start_timer(self):
        interval_ms = max(1, self.config.refresh_interval_minutes) * 60 * 1000
        self.refresh_timer.start(interval_ms)

    def _on_sort_changed(self, new_sort_order: str):
        self.config.sort_order = new_sort_order
        if hasattr(self.github_provider, "sort_order"):
            self.github_provider.sort_order = new_sort_order
        self.config_manager.save(self.config)

    def _on_settings_saved(self, new_config: AppConfig):
        self.config = new_config
        self.config_manager.save(new_config)

        if hasattr(self.github_provider, "update_config"):
            self.github_provider.update_config(
                token=new_config.github_token,
                repositories=new_config.repositories,
                sort_order=new_config.sort_order
            )

        if hasattr(self.jira_provider, "update_config"):
            self.jira_provider.update_config(
                jira_url=new_config.jira_url,
                email=new_config.jira_email,
                api_token=new_config.jira_api_token,
                jql=new_config.jira_jql
            )

        self._start_timer()
        self.status_bar.showMessage("Configurações salvas com sucesso!", 4000)
        self.start_fetch()
        self._switch_tab(0)

    def _on_test_notification(self):
        self.notifier.notify(
            "Dev Status Widget",
            "Notificação do GNOME funcionando perfeitamente! 🚀",
            urgency="normal"
        )
        self.status_bar.showMessage("Notificação de teste disparada!", 3000)

    def start_fetch(self):
        if self.is_fetching:
            return

        self.is_fetching = True
        self.prs_view.set_loading(True)
        self.jira_view.set_loading(True)
        self.status_bar.showMessage("Atualizando Pull Requests e Jira...")

        self.thread = QThread()
        self.worker = FetchWorker(self.github_provider, self.jira_provider)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_fetch_completed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _on_fetch_completed(self, results: dict):
        self.is_fetching = False
        self.prs_view.set_loading(False)
        self.jira_view.set_loading(False)

        pr_res = results.get("prs", {})
        jira_res = results.get("jira", {})

        pr_items = pr_res.get("items", [])
        pr_new = pr_res.get("new_items", [])
        pr_errors = pr_res.get("errors", [])

        jira_items = jira_res.get("items", [])
        jira_new = jira_res.get("new_items", [])
        jira_errors = jira_res.get("errors", [])

        # 1. Atualiza visualização de PRs
        self.prs_view.update_prs(pr_items)
        self.tab_prs.set_count(len(pr_items))
        if pr_errors:
            self.prs_view.set_error_message(" | ".join(pr_errors))
        else:
            self.prs_view.set_error_message(None)

        # 2. Atualiza visualização do Jira
        self.jira_view.update_tasks(jira_items)
        self.tab_jira.set_count(len(jira_items))
        if jira_errors:
            self.jira_view.set_error_message(" | ".join(jira_errors))
        else:
            self.jira_view.set_error_message(None)

        # 3. Notificações desktop de novos itens
        if self.config.notifications_enabled:
            if pr_new:
                self.notifier.notify_new_prs(pr_new)
            if jira_new:
                self.notifier.notify_new_jira_tasks(jira_new)

        # 4. Atualiza tooltip da bandeja
        pr_text = f"{len(pr_items)} PRs"
        jira_text = f"{len(jira_items)} Tarefas Jira"
        self.tray.setToolTip(f"Dev Status Widget - {pr_text} • {jira_text}")

        now_str = datetime.now().strftime("%H:%M:%S")
        self.status_bar.showMessage(f"Atualizado às {now_str} • {pr_text} • {jira_text}")

    def toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        if self.config.minimize_to_tray_on_close and self.tray.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "Dev Status Widget",
                "O aplicativo continua em execução na bandeja do sistema.",
                QIcon(self.icon_path) if os.path.exists(self.icon_path) else None,
                3000
            )
        else:
            self.quit_app()

    def quit_app(self):
        self.tray.hide()
        self.refresh_timer.stop()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(2000)
        self.close()

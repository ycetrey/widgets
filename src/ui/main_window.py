"""
Janela principal do aplicativo com suporte a abas, bandeja e auto-refresh.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
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
from ..core.database import DatabaseManager
from ..core.models import AppConfig
from ..core.notifier import DesktopNotifier
from ..core.sprint_freeze import generate_and_save
from ..core.updater import GitUpdater, UpdateInfo
from ..providers.github_provider import GitHubProvider
from ..providers.jira_provider import JiraProvider
from .dock_badge import DockBadgeManager
from .tray import SystemTrayManager
from .views.freeze_report_view import FreezeReportView
from .views.jira_view import JiraView
from .views.notifications_view import NotificationsView
from .views.prs_view import PullRequestsView
from .views.settings_view import SettingsView
from .widgets.tab_button import NavTabButton
from .widgets.update_banner import UpdateBannerWidget


class FetchWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(
        self,
        github_provider: GitHubProvider,
        jira_provider: JiraProvider = None,
        jira_enabled: bool = True,
        updater: GitUpdater = None,
    ):
        super().__init__()
        self.github_provider = github_provider
        self.jira_provider = jira_provider
        self.jira_enabled = jira_enabled
        self.updater = updater

    def run(self):
        pr_result = self.github_provider.fetch() if self.github_provider else {"items": [], "new_items": [], "errors": []}
        jira_result = (self.jira_provider.fetch() if self.jira_enabled else {"items": [], "new_items": [], "errors": []}) if self.jira_provider else {"items": [], "new_items": [], "errors": []}
        update_result = self.updater.check_for_updates() if self.updater else None
        self.finished.emit({
            "prs": pr_result,
            "jira": jira_result,
            "update": update_result,
        })


class CheckUpdateWorker(QObject):
    finished = pyqtSignal(object)

    def __init__(self, updater: GitUpdater):
        super().__init__()
        self.updater = updater

    def run(self):
        result = self.updater.check_for_updates() if self.updater else None
        self.finished.emit(result)


class FreezeReportWorker(QObject):
    # Emite (report: Optional[SprintFreezeReport], error: Optional[str]).
    # `error` só é preenchido quando algo realmente falhou (ex: PDF não
    # renderizou); report=None com error=None significa "sem sprint ativa
    # ou sem tarefas", um caso normal e silencioso.
    finished = pyqtSignal(object, object)

    def __init__(self, jira_provider, github_provider, db, production_branch: str, is_automatic: bool = False):
        super().__init__()
        self.jira_provider = jira_provider
        self.github_provider = github_provider
        self.db = db
        self.production_branch = production_branch
        self.is_automatic = is_automatic

    def run(self):
        try:
            report = generate_and_save(
                self.jira_provider,
                self.github_provider,
                self.db,
                self.production_branch,
                is_automatic=self.is_automatic
            )
            self.finished.emit(report, None)
        except Exception as e:
            print(f"[SprintFreeze] Erro ao gerar relatório: {e}")
            self.finished.emit(None, str(e))


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
                sort_order=self.config.sort_order,
                github_username=self.config.github_username
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

        base_dir = Path(__file__).resolve().parent.parent.parent
        sound_path = str(base_dir / "assets" / "sounds" / "notification.wav")
        self.notifier = DesktopNotifier(
            icon_path=self.icon_path,
            sound_path=sound_path,
            sound_enabled=self.config.sound_enabled
        )
        self.db = DatabaseManager()

        # Gerenciador de Atualizações Git
        self.updater = GitUpdater()
        self._last_notified_update_commit = None
        self._current_update_info: Optional[UpdateInfo] = None
        self.update_thread: QThread = None
        self.update_worker: CheckUpdateWorker = None

        # Worker e Thread
        self.thread: QThread = None
        self.worker: FetchWorker = None
        self.is_fetching = False

        # Relatório de Sprint Freeze
        self.is_generating_freeze_report = False
        self.freeze_thread: QThread = None
        self.freeze_worker: FreezeReportWorker = None
        self._last_jira_task_keys: list = []

        # Timer de auto-refresh
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.start_fetch)

        # Tray
        self.tray = SystemTrayManager(icon_path=self.icon_path, parent=self)
        self.notifier.set_tray_icon(self.tray)

        # Dock Badge (GNOME Dock / Dash to Dock)
        self.dock_badge = DockBadgeManager()

        self._init_ui()
        self._setup_tray_connections()
        self._setup_shortcuts()
        self._start_timer()

        # Timer de checagem da automação de Sprint Freeze (a cada hora)
        self.freeze_check_timer = QTimer(self)
        self.freeze_check_timer.timeout.connect(self._check_automatic_freeze_report)
        self.freeze_check_timer.start(60 * 60 * 1000)

        # Carrega dados do cache local SQLite imediatamente (carregamento instantâneo)
        self._load_from_cache()

        # Dispara primeira busca imediatamente
        self.start_fetch()

    def _load_from_cache(self):
        try:
            cached_prs = self.db.get_pull_requests()
            if cached_prs:
                self.prs_view.update_prs(cached_prs)
                self.tab_prs.set_count(len(cached_prs))

            if self.config.jira_enabled:
                cached_jira = self.db.get_jira_tasks()
                if cached_jira:
                    self.jira_view.update_tasks(cached_jira)
                    self.tab_jira.set_count(len(cached_jira))

            self._reload_notifications()
            self.freeze_report_view.set_reports(self.db.get_freeze_reports())
        except Exception as e:
            print(f"[Database] Erro ao carregar dados do cache inicial: {e}")

    def _init_ui(self):
        self.setWindowTitle("Dev Status Widget - Monitor de PRs e Jira")
        self.resize(1180, 780)
        self.setMinimumSize(680, 500)

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
        self.tab_jira.setVisible(self.config.jira_enabled)
        tab_layout.addWidget(self.tab_jira)

        # Aba 2: Notificações
        self.tab_notifications = NavTabButton("🔔 Notificações", count=0)
        self.tab_notifications.set_active(False)
        self.tab_notifications.clicked.connect(lambda: self._switch_tab(2))
        tab_layout.addWidget(self.tab_notifications)

        # Aba 3: Configurações
        self.tab_settings = NavTabButton("⚙️ Configurações", count=0)
        self.tab_settings.set_active(False)
        self.tab_settings.clicked.connect(lambda: self._switch_tab(3))
        tab_layout.addWidget(self.tab_settings)

        # Aba 4: Relatórios de Sprint Freeze
        self.tab_freeze = NavTabButton("🧊 Freeze", count=0)
        self.tab_freeze.set_active(False)
        self.tab_freeze.clicked.connect(lambda: self._switch_tab(4))
        self.tab_freeze.setVisible(self.config.freeze_reports_enabled and self.config.jira_enabled)
        tab_layout.addWidget(self.tab_freeze)

        tab_layout.addStretch()
        main_layout.addWidget(tab_frame)

        # Banner de Atualização Visual (oculto por padrão até detectar novidades)
        self.update_banner = UpdateBannerWidget(self)
        self.update_banner.update_requested.connect(self.prompt_and_perform_update)
        self.update_banner.details_requested.connect(self.show_update_details)
        main_layout.addWidget(self.update_banner)

        # 2. Pilha de Visualizações (StackedWidget)
        self.stack = QStackedWidget()

        # View 0: Pull Requests
        self.prs_view = PullRequestsView(
            sort_order=self.config.sort_order,
            current_user=self.config.github_username
        )
        self.prs_view.refresh_requested.connect(self.start_fetch)
        self.prs_view.sort_changed.connect(self._on_sort_changed)
        self.stack.addWidget(self.prs_view)

        # View 1: Jira Tarefas
        self.jira_view = JiraView()
        self.jira_view.refresh_requested.connect(self.start_fetch)
        self.stack.addWidget(self.jira_view)

        # View 2: Notificações
        self.notifications_view = NotificationsView()
        self.notifications_view.dismiss_one_requested.connect(self._on_dismiss_notification)
        self.notifications_view.clear_all_requested.connect(self._on_clear_all_notifications)
        self.notifications_view.update_requested.connect(self.prompt_and_perform_update)
        self.stack.addWidget(self.notifications_view)

        # View 3: Configurações
        self.settings_view = SettingsView(config=self.config)
        self.settings_view.settings_saved.connect(self._on_settings_saved)
        self.settings_view.test_notification_requested.connect(self._on_test_notification)
        self.settings_view.check_updates_requested.connect(self.check_for_updates_manual)
        self.settings_view.update_app_requested.connect(self.prompt_and_perform_update)
        self.stack.addWidget(self.settings_view)

        # View 4: Relatórios de Sprint Freeze
        self.freeze_report_view = FreezeReportView()
        self.freeze_report_view.generate_requested.connect(self._on_generate_freeze_report)
        self.freeze_report_view.download_requested.connect(self._on_download_freeze_report)
        self.stack.addWidget(self.freeze_report_view)

        main_layout.addWidget(self.stack, stretch=1)

        # 3. Barra de Status Inferior
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto")

    def _setup_tray_connections(self):
        self.tray.show()
        self.tray.toggle_window_requested.connect(self.toggle_window_visibility)
        self.tray.refresh_requested.connect(self.start_fetch)
        self.tray.open_settings_requested.connect(lambda: self._switch_tab(3))
        self.tray.update_requested.connect(self.prompt_and_perform_update)
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
        self.tab_notifications.set_active(index == 2)
        self.tab_settings.set_active(index == 3)
        self.tab_freeze.set_active(index == 4)

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
        self.notifier.set_sound_enabled(new_config.sound_enabled)

        if hasattr(self.github_provider, "update_config"):
            self.github_provider.update_config(
                token=new_config.github_token,
                repositories=new_config.repositories,
                sort_order=new_config.sort_order,
                github_username=new_config.github_username
            )

        self.prs_view.set_current_user(new_config.github_username)

        if hasattr(self.jira_provider, "update_config"):
            self.jira_provider.update_config(
                jira_url=new_config.jira_url,
                email=new_config.jira_email,
                api_token=new_config.jira_api_token,
                jql=new_config.jira_jql
            )

        self.tab_jira.setVisible(new_config.jira_enabled)
        self.tab_freeze.setVisible(new_config.freeze_reports_enabled and new_config.jira_enabled)
        if not new_config.jira_enabled and self.stack.currentIndex() == 1:
            self._switch_tab(0)

        self._start_timer()
        self.status_bar.showMessage("Configurações salvas com sucesso!", 4000)
        self.start_fetch()
        self._switch_tab(0)

    def _reload_notifications(self):
        try:
            active_notifs = self.db.get_active_notifications()
            self.notifications_view.set_notifications(active_notifs)
            count = len(active_notifs)
            self.tab_notifications.set_count(count)
            self.dock_badge.set_count(count)
        except Exception as e:
            print(f"[Database] Erro ao recarregar notificações: {e}")

    def _on_dismiss_notification(self, notif_id: int):
        try:
            self.db.dismiss_notification(notif_id)
            self._reload_notifications()
            self.status_bar.showMessage("Notificação removida.", 2500)
        except Exception as e:
            print(f"[Database] Erro ao remover notificação: {e}")

    def _on_clear_all_notifications(self):
        try:
            self.db.dismiss_all_notifications()
            self._reload_notifications()
            self.status_bar.showMessage("Todas as notificações foram limpas.", 2500)
        except Exception as e:
            print(f"[Database] Erro ao limpar notificações: {e}")

    def _on_test_notification(self):
        self.notifier.notify(
            "Dev Status Widget",
            "Notificação do GNOME funcionando perfeitamente! 🚀",
            urgency="normal"
        )
        try:
            self.db.add_notification(
                item_key=f"system:test:{datetime.now().timestamp()}",
                item_type="system",
                title="Dev Status Widget",
                message="Notificação do GNOME funcionando perfeitamente! 🚀",
                link_url=None
            )
            self._reload_notifications()
        except Exception as e:
            print(f"[Database] Erro ao registrar notificação de teste: {e}")
        self.status_bar.showMessage("Notificação de teste disparada!", 3000)

    def start_fetch(self):
        if self.is_fetching:
            return

        self.is_fetching = True
        self.prs_view.set_loading(True)
        self.jira_view.set_loading(True)
        self.status_bar.showMessage("Atualizando Pull Requests e Jira...")

        self.thread = QThread()
        self.worker = FetchWorker(
            self.github_provider,
            self.jira_provider,
            jira_enabled=self.config.jira_enabled,
            updater=self.updater,
        )
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
        update_res = results.get("update")

        if update_res is not None:
            self._handle_update_result(update_res)

        pr_items = pr_res.get("items", [])
        pr_new = pr_res.get("new_items", [])
        pr_errors = pr_res.get("errors", [])
        current_user = pr_res.get("current_user") or self.config.github_username
        if current_user:
            self.prs_view.set_current_user(current_user)
            if not self.config.github_username:
                self.config.github_username = current_user
                self.config_manager.save(self.config)

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
        jira_user = jira_res.get("current_user_name")
        self.jira_view.update_tasks(jira_items, current_user_name=jira_user)
        self._last_jira_task_keys = [t.key for t in jira_items if not t.is_subtask]
        self.tab_jira.set_count(len(jira_items))
        if jira_errors:
            self.jira_view.set_error_message(" | ".join(jira_errors))
        else:
            self.jira_view.set_error_message(None)

        # Salva dados no banco local SQLite
        if pr_items:
            try:
                self.db.save_pull_requests(pr_items)
            except Exception as e:
                print(f"[Database] Erro ao salvar PRs no SQLite: {e}")

        if jira_items:
            try:
                self.db.save_jira_tasks(jira_items)
            except Exception as e:
                print(f"[Database] Erro ao salvar tarefas do Jira no SQLite: {e}")

        # 3. Notificações desktop de novos itens persistidas no SQLite
        if self.config.notifications_enabled:
            try:
                db_pr_new = self.db.detect_and_record_new_prs(pr_items) if pr_items else []
                db_jira_new = self.db.detect_and_record_new_jira(jira_items) if jira_items else []
                if db_pr_new:
                    self.notifier.notify_new_prs(db_pr_new)
                    for pr in db_pr_new:
                        title = f"Nova PR em {pr.repo}"
                        msg = f"#{pr.number}: {pr.title}\npor @{pr.author}"
                        self.db.add_notification(
                            item_key=f"pr:{pr.id}",
                            item_type="pr",
                            title=title,
                            message=msg,
                            link_url=pr.html_url
                        )
                if db_jira_new:
                    self.notifier.notify_new_jira_tasks(db_jira_new)
                    for task in db_jira_new:
                        title = f"Nova Tarefa Jira: {task.key}"
                        msg = f"{task.summary}\nStatus: {task.status} | Prioridade: {task.priority}"
                        self.db.add_notification(
                            item_key=f"jira:{task.key}",
                            item_type="jira",
                            title=title,
                            message=msg,
                            link_url=task.html_url
                        )
                if db_pr_new or db_jira_new:
                    self._reload_notifications()
            except Exception as e:
                print(f"[Database] Erro ao processar notificações no SQLite: {e}")

        # 4. Atualiza tooltip da bandeja
        pr_text = f"{len(pr_items)} PRs"
        now_str = datetime.now().strftime("%H:%M:%S")
        if self.config.jira_enabled:
            jira_text = f"{len(jira_items)} Tarefas Jira"
            self.tray.setToolTip(f"Dev Status Widget - {pr_text} • {jira_text}")
            self.status_bar.showMessage(f"Atualizado às {now_str} • {pr_text} • {jira_text}")
        else:
            self.tray.setToolTip(f"Dev Status Widget - {pr_text}")
            self.status_bar.showMessage(f"Atualizado às {now_str} • {pr_text}")

    def _handle_update_result(self, update_info: Optional[UpdateInfo]):
        if not update_info:
            return

        self._current_update_info = update_info
        self.settings_view.set_update_status(update_info)

        if update_info.available:
            self.update_banner.show_update(update_info)
            self.tray.set_update_available(True, commit_count=update_info.commits_behind)

            # Notifica via desktop apenas uma vez por commit remoto novo para evitar spam a cada ciclo
            if self._last_notified_update_commit != update_info.remote_commit:
                self._last_notified_update_commit = update_info.remote_commit
                if self.config.notifications_enabled:
                    self.notifier.notify_update(update_info, on_update_callback=self.prompt_and_perform_update)
                    try:
                        commit_text = "commit novo" if update_info.commits_behind == 1 else "commits novos"
                        self.db.add_notification(
                            item_key=f"update:{update_info.remote_commit}",
                            item_type="update",
                            title="🚀 Nova versão disponível!",
                            message=f"Há {update_info.commits_behind} {commit_text} no GitHub (branch {update_info.branch}).",
                            link_url=None
                        )
                        self._reload_notifications()
                    except Exception as e:
                        print(f"[Database] Erro ao registrar notificação de update: {e}")
        else:
            self.update_banner.setVisible(False)
            self.tray.set_update_available(False)

    def check_for_updates_manual(self):
        """Dispara verificação manual de atualizações a partir da aba de configurações."""
        self.settings_view.set_checking_updates(True)
        self.status_bar.showMessage("Verificando atualizações no GitHub...")

        self.update_thread = QThread()
        self.update_worker = CheckUpdateWorker(self.updater)
        self.update_worker.moveToThread(self.update_thread)

        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.finished.connect(self._on_manual_update_check_completed)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.finished.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)

        self.update_thread.start()

    def _on_manual_update_check_completed(self, update_info: Optional[UpdateInfo]):
        self._handle_update_result(update_info)
        if update_info and update_info.available:
            self.status_bar.showMessage(f"Atualização disponível: {update_info.commits_behind} commit(s) novo(s).", 4000)
        elif update_info and update_info.error:
            self.status_bar.showMessage(f"Erro ao verificar atualizações: {update_info.error}", 4000)
        else:
            self.status_bar.showMessage("Dev Status Widget está na versão mais recente.", 4000)

    def show_update_details(self):
        """Exibe popup com as novidades e commits da atualização disponível."""
        if not self._current_update_info or not self._current_update_info.changelog:
            QMessageBox.information(
                self,
                "Detalhes da Atualização",
                "Nenhum resumo de commits disponível no momento."
            )
            return

        commits_formatted = "\n".join(f"• {c}" for c in self._current_update_info.changelog)
        QMessageBox.information(
            self,
            "Novidades da Nova Versão",
            f"Repositório: ycetrey/widgets (branch: {self._current_update_info.branch})\n\n"
            f"Commits disponíveis:\n{commits_formatted}"
        )

    def _on_generate_freeze_report(self):
        if self.is_generating_freeze_report:
            return
        if not self.config.jira_enabled:
            self.status_bar.showMessage(
                "Habilite a integração com o Jira nas Configurações antes de gerar o relatório de freeze.", 5000
            )
            return

        self.is_generating_freeze_report = True
        self.freeze_report_view.set_generating(True)
        self.status_bar.showMessage("Gerando relatório de Sprint Freeze...")
        self._start_freeze_generation(is_automatic=False)

    def _start_freeze_generation(self, is_automatic: bool):
        self.freeze_thread = QThread()
        self.freeze_worker = FreezeReportWorker(
            self.jira_provider,
            self.github_provider,
            self.db,
            self.config.freeze_production_branch,
            is_automatic=is_automatic
        )
        self.freeze_worker.moveToThread(self.freeze_thread)

        self.freeze_thread.started.connect(self.freeze_worker.run)
        self.freeze_worker.finished.connect(self._on_freeze_report_generated)
        self.freeze_worker.finished.connect(self.freeze_thread.quit)
        self.freeze_worker.finished.connect(self.freeze_worker.deleteLater)
        self.freeze_thread.finished.connect(self.freeze_thread.deleteLater)

        self.freeze_thread.start()

    def _on_freeze_report_generated(self, report, error):
        self.is_generating_freeze_report = False
        self.freeze_report_view.set_generating(False)

        if error:
            QMessageBox.critical(
                self, "Erro ao Gerar Relatório",
                f"Ocorreu um erro ao gerar o relatório de Sprint Freeze:\n\n{error}\n\n"
                "Se o erro mencionar bibliotecas do WeasyPrint, rode o install.sh novamente."
            )
            self.status_bar.showMessage("Erro ao gerar relatório de Sprint Freeze.", 5000)
            return

        if report is None:
            self.status_bar.showMessage(
                "Não foi possível gerar o relatório: nenhuma sprint ativa encontrada.", 5000
            )
            return

        self.freeze_report_view.set_reports(self.db.get_freeze_reports())
        self.status_bar.showMessage(
            f"Relatório de Freeze gerado: {report.promoted_count} promovidas / {report.retained_count} retidas.",
            5000
        )

    def _on_download_freeze_report(self, pdf_path: str):
        if not pdf_path or not os.path.exists(pdf_path):
            QMessageBox.warning(
                self, "Arquivo não encontrado",
                "O arquivo PDF deste relatório não foi encontrado no disco."
            )
            return

        suggested_name = os.path.basename(pdf_path)
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório de Freeze", suggested_name, "PDF (*.pdf)"
        )
        if dest_path:
            try:
                shutil.copyfile(pdf_path, dest_path)
                self.status_bar.showMessage(f"Relatório salvo em {dest_path}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao salvar", f"Não foi possível salvar o arquivo:\n{e}")

    def _check_automatic_freeze_report(self):
        if not (self.config.freeze_reports_enabled and self.config.jira_enabled):
            return
        if self.is_generating_freeze_report:
            return
        if not self._last_jira_task_keys:
            return

        from datetime import date
        from ..core.sprint_freeze import should_generate_automatic_report

        sprint_info = self.jira_provider.get_active_sprint(self._last_jira_task_keys[0])
        if sprint_info is None:
            return

        already_has_automatic = self.db.has_automatic_freeze_report(str(sprint_info.id))
        if should_generate_automatic_report(date.today(), sprint_info.end_date, already_has_automatic):
            self.is_generating_freeze_report = True
            self.freeze_report_view.set_generating(True)
            self.status_bar.showMessage(
                "Gerando relatório automático de Sprint Freeze (segunda-feira de virada)...", 5000
            )
            self._start_freeze_generation(is_automatic=True)

    def prompt_and_perform_update(self):
        """Solicita confirmação e executa o git pull e reinicialização do aplicativo."""
        if self.isHidden() or self.isMinimized():
            self.showNormal()
            self.activateWindow()

        # Confirmação do usuário (respeitando skip_permissions)
        if not getattr(self.config, "skip_permissions", False):
            behind_str = f" ({self._current_update_info.commits_behind} novidade(s))" if self._current_update_info else ""
            reply = QMessageBox.question(
                self,
                "Confirmar Atualização",
                f"Deseja atualizar o Dev Status Widget agora{behind_str}?\n\n"
                "O aplicativo executará 'git pull' e será reiniciado automaticamente.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Checagem preventiva de alterações locais para não sobrescrever trabalho
        if self.updater.has_local_changes():
            QMessageBox.warning(
                self,
                "Alterações Locais Detectadas",
                "Existem arquivos modificados localmente no repositório.\n"
                "Por favor, descarte ou faça commit das suas alterações antes de atualizar."
            )
            return

        self.status_bar.showMessage("Atualizando repositório via git pull...")
        QApplication.processEvents()

        success, msg = self.updater.apply_update()
        if success:
            self.status_bar.showMessage("Atualização concluída com sucesso! Reiniciando aplicativo...", 3000)
            QApplication.processEvents()
            self.updater.restart_application()
        else:
            QMessageBox.critical(
                self,
                "Erro na Atualização",
                f"Ocorreu um erro ao executar git pull:\n\n{msg}"
            )
            self.status_bar.showMessage("Erro ao atualizar repositório.")

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
        if hasattr(self, "dock_badge"):
            self.dock_badge.clear()
        self.tray.hide()
        self.refresh_timer.stop()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(2000)
        self.close()

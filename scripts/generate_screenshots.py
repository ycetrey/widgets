#!/usr/bin/env python3
"""
Gera capturas de tela das abas do Dev Status Widget com dados fictícios de exemplo.
Garante 100% de privacidade: tokens mascarados, dados fictícios e zero vazamento de informações sigilosas.
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Adiciona raiz do projeto ao PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

from src.core.config import ConfigManager
from src.core.database import DatabaseManager
from src.core.models import AppConfig, PullRequestItem, JiraTaskItem, NotificationItem
from src.core.updater import UpdateInfo
from src.ui.main_window import MainWindow
from src.ui.theme import apply_theme


def create_sample_data():
    now = datetime.now(timezone.utc)

    # 1. Pull Requests fictícias (projetos open source / públicos)
    prs = [
        PullRequestItem(
            id=101,
            number=42,
            title="feat: auto update detection and clean background reload",
            repo="ycetrey/widgets",
            author="developer",
            author_avatar="",
            html_url="https://github.com/ycetrey/widgets/pull/42",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
            is_draft=False,
            labels=["desktop", "enhancement"],
            comments_count=3,
            review_decision="APPROVED",
            checks_summary="35/35",
            checks_state="SUCCESS"
        ),
        PullRequestItem(
            id=102,
            number=30421,
            title="feat(compiler): optimize reactive scope memoization",
            repo="facebook/react",
            author="sophiebits",
            author_avatar="",
            html_url="https://github.com/facebook/react/pull/30421",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1),
            is_draft=False,
            labels=["compiler", "react-19"],
            comments_count=7,
            review_decision="REVIEW_REQUIRED",
            checks_summary="12/12",
            checks_state="SUCCESS"
        ),
        PullRequestItem(
            id=103,
            number=67120,
            title="net/http: improve HTTP/2 connection pooling under high concurrency",
            repo="golang/go",
            author="bradfitz",
            author_avatar="",
            html_url="https://github.com/golang/go/pull/67120",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=3),
            is_draft=False,
            labels=["networking", "performance"],
            comments_count=14,
            review_decision="REVIEW_REQUIRED",
            checks_summary="8/8",
            checks_state="SUCCESS"
        ),
        PullRequestItem(
            id=104,
            number=124501,
            title="fix(scheduler): prevent pod preemption deadlocks in multi-tenant clusters",
            repo="kubernetes/kubernetes",
            author="liggitt",
            author_avatar="",
            html_url="https://github.com/kubernetes/kubernetes/pull/124501",
            created_at=now - timedelta(days=16),
            updated_at=now - timedelta(days=4),
            is_draft=False,
            labels=["sig/scheduling", "priority/critical"],
            comments_count=22,
            review_decision="CHANGES_REQUESTED",
            checks_summary="42/45",
            checks_state="FAILURE"
        ),
    ]

    # 2. Tarefas Jira fictícias (chaves e resumos genéricos)
    jira_tasks = [
        JiraTaskItem(
            key="CORE-104",
            summary="Implementar autenticação OAuth2 PKCE para o client desktop",
            status="Em Andamento",
            status_category="indeterminate",
            priority="High",
            issue_type="Story",
            assignee="Developer",
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(minutes=45),
            html_url="https://jira.exemplo.com/browse/CORE-104"
        ),
        JiraTaskItem(
            key="API-308",
            summary="Refatorar serviço de despacho de notificações assíncronas",
            status="Code Review",
            status_category="indeterminate",
            priority="Highest",
            issue_type="Improvement",
            assignee="Developer",
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(hours=2),
            html_url="https://jira.exemplo.com/browse/API-308"
        ),
        JiraTaskItem(
            key="DEV-205",
            summary="Otimizar índices no banco SQLite para queries de alto volume",
            status="A Fazer",
            status_category="new",
            priority="Medium",
            issue_type="Task",
            assignee="Developer",
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=5),
            html_url="https://jira.exemplo.com/browse/DEV-205"
        ),
        JiraTaskItem(
            key="FEAT-401",
            summary="Integrar menu contextual dinâmico na bandeja do GNOME",
            status="Concluído",
            status_category="done",
            priority="High",
            issue_type="Story",
            assignee="Developer",
            created_at=now - timedelta(days=6),
            updated_at=now - timedelta(days=1),
            html_url="https://jira.exemplo.com/browse/FEAT-401"
        ),
    ]

    # 3. Notificações fictícias
    notifications = [
        NotificationItem(
            id=1,
            item_key="update:8c0025d",
            item_type="update",
            title="🚀 Nova versão disponível!",
            message="Há 3 novo(s) commit(s) no repositório GitHub (branch main). Clique para atualizar e reiniciar.",
            link_url=None,
            created_at=now - timedelta(minutes=5)
        ),
        NotificationItem(
            id=2,
            item_key="pr:42",
            item_type="pr",
            title="Nova PR em ycetrey/widgets",
            message="#42: feat: auto update detection and clean background reload\npor @developer",
            link_url="https://github.com/ycetrey/widgets/pull/42",
            created_at=now - timedelta(hours=1)
        ),
        NotificationItem(
            id=3,
            item_key="jira:API-308",
            item_type="jira",
            title="Nova Tarefa Jira: API-308",
            message="Refatorar serviço de despacho de notificações assíncronas\nStatus: Code Review | Prioridade: Highest",
            link_url="https://jira.exemplo.com/browse/API-308",
            created_at=now - timedelta(hours=3)
        ),
        NotificationItem(
            id=4,
            item_key="pr:30421",
            item_type="pr",
            title="Nova PR em facebook/react",
            message="#30421: feat(compiler): optimize reactive scope memoization\npor @sophiebits",
            link_url="https://github.com/facebook/react/pull/30421",
            created_at=now - timedelta(days=1)
        ),
    ]

    # 4. Configuração 100% segura e sanitizada
    config = AppConfig(
        github_token="ghp_••••••••••••••••••••••••••••••••",
        github_username="developer",
        repositories=["ycetrey/widgets", "facebook/react", "golang/go", "kubernetes/kubernetes"],
        refresh_interval_minutes=5,
        sort_order="oldest_first",
        notifications_enabled=True,
        sound_enabled=True,
        minimize_to_tray_on_close=True,
        start_minimized=False,
        dark_mode=True,
        jira_enabled=True,
        jira_url="https://sua-empresa.atlassian.net",
        jira_email="dev@empresa.com",
        jira_api_token="ATATT3xFfGF0••••••••••••••••••••••",
        jira_jql="assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC",
        autostart=True
    )

    return prs, jira_tasks, notifications, config


def generate():
    output_dir = BASE_DIR / "assets" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(["-platform", "offscreen"])
    apply_theme(app, dark_mode=True)

    # Configuração temporária isolada
    tmp_config = BASE_DIR / "assets" / "screenshots" / ".tmp_config.yaml"
    cm = ConfigManager(custom_path=str(tmp_config))

    prs, jira_tasks, notifications, config = create_sample_data()
    cm.save(config)

    icon_path = str(BASE_DIR / "assets" / "icon.png")

    class DummyProvider:
        def fetch(self):
            return {"items": prs, "new_items": [], "errors": []}

    class DummyJiraProvider:
        def fetch(self):
            return {"items": jira_tasks, "new_items": [], "errors": []}

    window = MainWindow(
        config_manager=cm,
        icon_path=icon_path,
        provider=DummyProvider(),
        jira_provider=DummyJiraProvider()
    )
    window.resize(1180, 760)

    # Injeta dados de exemplo e ajusta estados visuais
    window.is_fetching = False
    window.prs_view.set_loading(False)
    window.jira_view.set_loading(False)
    window.status_bar.showMessage("Pronto • 4 PRs • 4 Tarefas Jira")

    window.prs_view.update_prs(prs)
    window.tab_prs.set_count(len(prs))

    window.jira_view.update_tasks(jira_tasks)
    window.tab_jira.set_count(len(jira_tasks))

    window.notifications_view.set_notifications(notifications)
    window.tab_notifications.set_count(len(notifications))

    window.settings_view.load_config(config)

    # Configura status do updater na tela de settings
    mock_update_info = UpdateInfo(
        available=True,
        current_commit="8c0025d",
        remote_commit="9e1134a",
        branch="main",
        commits_behind=3,
        changelog=[
            "feat: auto update detection and clean background reload (8c0025d)",
            "ui: add dynamic banner and tray actions for updates (a1b2c3d)",
            "fix: prevent local git conflicts before applying pull (e4f5g6h)"
        ]
    )
    window.settings_view.set_update_status(mock_update_info)
    window.update_banner.show_update(mock_update_info)

    # 1. Print da Aba Pull Requests (com o UpdateBanner ativo)
    window._switch_tab(0)
    window.show()
    QApplication.processEvents()
    pix_prs = window.grab()
    pix_prs.save(str(output_dir / "01_pull_requests.png"))
    print("✓ Gerado: 01_pull_requests.png")

    # 2. Print da Aba Jira Tarefas (Kanban)
    window._switch_tab(1)
    QApplication.processEvents()
    pix_jira = window.grab()
    pix_jira.save(str(output_dir / "02_jira_tarefas.png"))
    print("✓ Gerado: 02_jira_tarefas.png")

    # 3. Print da Aba Notificações
    window._switch_tab(2)
    QApplication.processEvents()
    pix_notif = window.grab()
    pix_notif.save(str(output_dir / "03_notificacoes.png"))
    print("✓ Gerado: 03_notificacoes.png")

    # 4. Print da Aba Configurações (Topo: Repositórios, GitHub, Jira)
    window._switch_tab(3)
    scroll_area = window.settings_view.findChild(type(window.settings_view.scroll)) if hasattr(window.settings_view, 'scroll') else None
    # Rola para o topo
    for child in window.settings_view.children():
        if hasattr(child, 'verticalScrollBar'):
            child.verticalScrollBar().setValue(0)
    QApplication.processEvents()
    pix_settings = window.grab()
    pix_settings.save(str(output_dir / "04_configuracoes_repos_auth.png"))
    print("✓ Gerado: 04_configuracoes_repos_auth.png")

    # 5. Print da Aba Configurações (Parte Inferior: Preferências e Atualizações)
    for child in window.settings_view.children():
        if hasattr(child, 'verticalScrollBar'):
            child.verticalScrollBar().setValue(child.verticalScrollBar().maximum())
    QApplication.processEvents()
    pix_settings_bottom = window.grab()
    pix_settings_bottom.save(str(output_dir / "05_configuracoes_preferencias_updates.png"))
    print("✓ Gerado: 05_configuracoes_preferencias_updates.png")

    # Limpeza do arquivo de configuração temporário
    if tmp_config.exists():
        tmp_config.unlink()

    print(f"\nTodas as capturas de tela foram geradas com sucesso em: {output_dir}")


if __name__ == "__main__":
    generate()

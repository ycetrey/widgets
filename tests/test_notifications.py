"""
Testes automatizados para a gestão, ordenação, persistência e remoção de notificações.
"""
import os
import unittest
from datetime import datetime, timezone, timedelta

from src.core.database import DatabaseManager
from src.core.models import NotificationItem, PullRequestItem, JiraTaskItem


class TestNotifications(unittest.TestCase):
    def setUp(self):
        self.tmp_db = "tests_tmp_notifications.db"
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)
        self.db = DatabaseManager(custom_path=self.tmp_db)

    def tearDown(self):
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)

    def test_notification_time_humanized(self):
        now = datetime.now(timezone.utc)
        n_recent = NotificationItem(
            id=1, item_key="k1", item_type="system",
            title="T1", message="M1", created_at=now - timedelta(seconds=20)
        )
        self.assertIn("segundos", n_recent.time_humanized)

        n_min = NotificationItem(
            id=2, item_key="k2", item_type="pr",
            title="T2", message="M2", created_at=now - timedelta(minutes=15)
        )
        self.assertIn("15 min", n_min.time_humanized)

        n_hours = NotificationItem(
            id=3, item_key="k3", item_type="jira",
            title="T3", message="M3", created_at=now - timedelta(hours=3)
        )
        self.assertIn("3 h", n_hours.time_humanized)

    def test_add_and_sort_newest_first(self):
        now = datetime.now(timezone.utc)

        # Adiciona notificações com datas distintas
        n1 = self.db.add_notification(
            item_key="pr:101",
            item_type="pr",
            title="PR Antiga",
            message="Mensagem 1",
            link_url="https://github.com/pr/101",
            created_at=now - timedelta(hours=2)
        )
        n2 = self.db.add_notification(
            item_key="jira:FF-1",
            item_type="jira",
            title="Tarefa Mais Nova",
            message="Mensagem 2",
            link_url="https://jira.com/FF-1",
            created_at=now - timedelta(minutes=5)
        )
        n3 = self.db.add_notification(
            item_key="system:test",
            item_type="system",
            title="Notificação Recente",
            message="Mensagem 3",
            created_at=now
        )

        active = self.db.get_active_notifications()
        self.assertEqual(len(active), 3)

        # Deve estar estritamente ordenada da mais nova para a mais antiga
        self.assertEqual(active[0].title, "Notificação Recente")
        self.assertEqual(active[1].title, "Tarefa Mais Nova")
        self.assertEqual(active[2].title, "PR Antiga")

    def test_dismiss_one_notification(self):
        now = datetime.now(timezone.utc)
        n1 = self.db.add_notification("pr:1", "pr", "PR 1", "Msg", created_at=now - timedelta(minutes=10))
        n2 = self.db.add_notification("pr:2", "pr", "PR 2", "Msg", created_at=now)

        active_before = self.db.get_active_notifications()
        self.assertEqual(len(active_before), 2)

        # Remove n2 individualmente
        self.db.dismiss_notification(n2.id)

        active_after = self.db.get_active_notifications()
        self.assertEqual(len(active_after), 1)
        self.assertEqual(active_after[0].id, n1.id)
        self.assertEqual(active_after[0].title, "PR 1")

    def test_dismiss_all_notifications(self):
        now = datetime.now(timezone.utc)
        self.db.add_notification("k1", "pr", "PR 1", "Msg", created_at=now - timedelta(minutes=10))
        self.db.add_notification("k2", "jira", "Jira 1", "Msg", created_at=now - timedelta(minutes=5))
        self.db.add_notification("k3", "system", "Sys 1", "Msg", created_at=now)

        self.assertEqual(len(self.db.get_active_notifications()), 3)

        # Limpa todas as notificações
        self.db.dismiss_all_notifications()

        active = self.db.get_active_notifications()
        self.assertEqual(len(active), 0)

    def test_removed_notification_is_not_re_added_on_next_fetch(self):
        now = datetime.now(timezone.utc)
        pr = PullRequestItem(
            id=200, number=55, title="Fix security", repo="repo1",
            author="dev", author_avatar="", html_url="https://url",
            created_at=now
        )

        # 1ª busca: inicializa o rastreador notifications_seen
        new_first = self.db.detect_and_record_new_prs([pr])
        self.assertEqual(len(new_first), 0)

        # Nova PR surge
        pr_new = PullRequestItem(
            id=201, number=56, title="Nova PR Importante", repo="repo1",
            author="dev2", author_avatar="", html_url="https://url2",
            created_at=now
        )
        detected = self.db.detect_and_record_new_prs([pr, pr_new])
        self.assertEqual(len(detected), 1)
        self.assertEqual(detected[0].id, 201)

        # Adiciona no histórico de notificações
        notif = self.db.add_notification(
            item_key=f"pr:{pr_new.id}",
            item_type="pr",
            title=f"Nova PR em {pr_new.repo}",
            message=pr_new.title,
            link_url=pr_new.html_url
        )
        self.assertEqual(len(self.db.get_active_notifications()), 1)

        # Usuário remove a notificação da lista
        self.db.dismiss_notification(notif.id)
        self.assertEqual(len(self.db.get_active_notifications()), 0)

        # Na próxima sincronização com as mesmas PRs, a notificação NÃO reaparece
        subsequent = self.db.detect_and_record_new_prs([pr, pr_new])
        self.assertEqual(len(subsequent), 0)
        self.assertEqual(len(self.db.get_active_notifications()), 0)


class TestNotificationsView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_view_order_and_signals(self):
        from src.ui.views.notifications_view import NotificationsView
        now = datetime.now(timezone.utc)

        view = NotificationsView()
        self.assertFalse(view.clear_all_btn.isEnabled())
        self.assertIn("0 itens", view.count_badge.text())

        n_older = NotificationItem(id=1, item_key="k1", item_type="pr", title="PR Antiga", message="M1", created_at=now - timedelta(hours=1))
        n_newer = NotificationItem(id=2, item_key="k2", item_type="jira", title="Jira Recente", message="M2", created_at=now)

        # Atualiza a view passando na ordem invertida
        view.set_notifications([n_older, n_newer])

        # A view deve ordenar automaticamente: mais recente primeiro
        self.assertEqual(len(view.notifications), 2)
        self.assertEqual(view.notifications[0].title, "Jira Recente")
        self.assertEqual(view.notifications[1].title, "PR Antiga")
        self.assertTrue(view.clear_all_btn.isEnabled())
        self.assertEqual(view.count_badge.text(), "2 itens")

        # Testa sinal de dismiss_one ao clicar no botão do card
        dismissed_ids = []
        view.dismiss_one_requested.connect(dismissed_ids.append)

        card_newer = view.cards_layout.itemAt(0).widget()
        card_newer.dismiss_clicked.emit(card_newer.notification.id)
        self.assertEqual(dismissed_ids, [2])

        # Testa sinal de clear_all_requested
        clear_requested = []
        view.clear_all_requested.connect(lambda: clear_requested.append(True))
        view.clear_all_btn.click()
        self.assertEqual(clear_requested, [True])


class TestMainWindowNotificationsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.tmp_config = "tests_tmp_mw_config.yaml"
        self.tmp_db = "tests_tmp_mw_db.db"
        for f in (self.tmp_config, self.tmp_db):
            if os.path.exists(f):
                os.remove(f)

    def tearDown(self):
        for f in (self.tmp_config, self.tmp_db):
            if os.path.exists(f):
                os.remove(f)

    def test_main_window_notifications_tabs_and_actions(self):
        from src.core.config import ConfigManager
        from src.ui.main_window import MainWindow
        from src.providers.mock_provider import MockProvider
        from src.providers.jira_provider import JiraProvider

        cm = ConfigManager(custom_path=self.tmp_config)
        cm.config.jira_enabled = True

        provider = MockProvider()
        jira_provider = JiraProvider(demo_mode=True)

        window = MainWindow(
            config_manager=cm,
            icon_path="",
            provider=provider,
            jira_provider=jira_provider
        )
        # Substitui db pelo db isolado de teste
        window.db = DatabaseManager(custom_path=self.tmp_db)

        # Insere notificação
        n = window.db.add_notification("pr:100", "pr", "PR Teste", "Corpo")
        window._reload_notifications()

        self.assertEqual(window.tab_notifications.count, 1)
        self.assertEqual(len(window.notifications_view.notifications), 1)

        # Alterna para a aba 2 (Notificações)
        window._switch_tab(2)
        self.assertEqual(window.stack.currentIndex(), 2)
        self.assertEqual(window.tab_notifications.property("active"), "true")

        # Testa remoção individual
        window._on_dismiss_notification(n.id)
        self.assertEqual(window.tab_notifications.count, 0)
        self.assertEqual(len(window.notifications_view.notifications), 0)

        # Testa dismiss all
        window.db.add_notification("pr:101", "pr", "PR Teste 2", "Corpo 2")
        window.db.add_notification("pr:102", "pr", "PR Teste 3", "Corpo 3")
        window._reload_notifications()
        self.assertEqual(window.tab_notifications.count, 2)

        window._on_clear_all_notifications()
        self.assertEqual(window.tab_notifications.count, 0)
        self.assertEqual(len(window.notifications_view.notifications), 0)

        # Limpeza
        window.tray.hide()
        window.refresh_timer.stop()


class TestDesktopNotifierSound(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_notifier_sound_toggle_and_play(self):
        from src.core.notifier import DesktopNotifier
        from pathlib import Path

        sound_path = str(Path(__file__).resolve().parent.parent / "assets" / "sounds" / "notification.wav")
        notifier = DesktopNotifier(sound_path=sound_path, sound_enabled=True)
        self.assertTrue(notifier.sound_enabled)
        self.assertEqual(notifier.sound_path, sound_path)

        # Reprodução com som ativo
        notifier.play_sound(force=True)
        self.assertGreater(notifier._last_sound_time, 0.0)

        # Debounce: chamada imediata sem force não atualiza _last_sound_time
        prev_time = notifier._last_sound_time
        notifier.play_sound(force=False)
        self.assertEqual(notifier._last_sound_time, prev_time)

        # Desativa som
        notifier.set_sound_enabled(False)
        self.assertFalse(notifier.sound_enabled)
        notifier.play_sound(force=True)
        self.assertEqual(notifier._last_sound_time, prev_time)


if __name__ == "__main__":
    unittest.main()

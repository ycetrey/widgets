"""
Testes unitários e de integração para o módulo de atualização Git, Banner e Tray.
"""
import os
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from src.core.updater import GitUpdater, UpdateInfo
from src.core.config import ConfigManager
from src.core.database import DatabaseManager
from src.ui.widgets.update_banner import UpdateBannerWidget
from src.ui.tray import SystemTrayManager


class TestGitUpdater(unittest.TestCase):
    def setUp(self):
        self.updater = GitUpdater(repo_dir=Path(__file__).resolve().parent.parent)

    def test_get_current_branch(self):
        branch = self.updater.get_current_branch()
        self.assertIsInstance(branch, str)
        self.assertTrue(len(branch) > 0)

    def test_get_current_commit(self):
        commit = self.updater.get_current_commit()
        self.assertIsInstance(commit, str)
        self.assertTrue(len(commit) >= 7)

    @patch.object(GitUpdater, "_run_git")
    def test_check_for_updates_no_update(self, mock_run):
        def side_effect(args, **kwargs):
            if "rev-parse" in args and "--abbrev-ref" in args:
                return 0, "main", ""
            if "rev-parse" in args and "HEAD" in args:
                return 0, "abc1234", ""
            if "fetch" in args:
                return 0, "", ""
            if "rev-parse" in args and "origin/main" in args:
                return 0, "abc1234", ""
            return 0, "", ""

        mock_run.side_effect = side_effect
        info = self.updater.check_for_updates()
        self.assertFalse(info.available)
        self.assertEqual(info.commits_behind, 0)

    @patch.object(GitUpdater, "_run_git")
    def test_check_for_updates_available(self, mock_run):
        def side_effect(args, **kwargs):
            if "rev-parse" in args and "--abbrev-ref" in args:
                return 0, "main", ""
            if "rev-parse" in args and "HEAD" in args:
                return 0, "1111111", ""
            if "fetch" in args:
                return 0, "", ""
            if "rev-parse" in args and "origin/main" in args:
                return 0, "2222222", ""
            if "rev-list" in args:
                return 0, "2", ""
            if "log" in args:
                return 0, "feat: nova feature (2222222)\nfix: ajuste (1234567)", ""
            return 0, "", ""

        mock_run.side_effect = side_effect
        info = self.updater.check_for_updates()
        self.assertTrue(info.available)
        self.assertEqual(info.commits_behind, 2)
        self.assertEqual(len(info.changelog), 2)
        self.assertIn("Nova atualização disponível", info.summary)

    @patch.object(GitUpdater, "_run_git")
    def test_apply_update_has_local_changes(self, mock_run):
        mock_run.return_value = (0, " M src/main.py", "")
        success, msg = self.updater.apply_update()
        self.assertFalse(success)
        self.assertIn("modificados", msg)

    @patch.object(GitUpdater, "has_local_changes")
    @patch.object(GitUpdater, "_run_git")
    def test_apply_update_success(self, mock_run, mock_has_changes):
        mock_has_changes.return_value = False
        mock_run.return_value = (0, "Updating 1111..2222\nFast-forward", "")
        success, msg = self.updater.apply_update()
        self.assertTrue(success)
        self.assertIn("sucesso", msg)


class TestUpdateUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_update_banner_widget(self):
        banner = UpdateBannerWidget()
        self.assertFalse(banner.isVisible())

        info = UpdateInfo(
            available=True,
            current_commit="1111111",
            remote_commit="2222222",
            branch="main",
            commits_behind=3,
            changelog=["commit 1", "commit 2", "commit 3"]
        )
        banner.show_update(info)
        self.assertTrue(banner.isVisible())
        self.assertIn("3 novo(s) commit(s)", banner.msg_lbl.text())

        # Testa dismiss
        banner._dismiss()
        self.assertFalse(banner.isVisible())

    def test_tray_update_action(self):
        tray = SystemTrayManager(icon_path="")
        self.assertFalse(tray.update_action.isVisible())

        tray.set_update_available(True, commit_count=2)
        self.assertTrue(tray.update_action.isVisible())
        self.assertIn("2 novos", tray.update_action.text())

        tray.set_update_available(False)
        self.assertFalse(tray.update_action.isVisible())


class TestMainWindowUpdateFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.tmp_config = "tests_tmp_updater_config.yaml"
        self.tmp_db = "tests_tmp_updater_db.db"
        for f in (self.tmp_config, self.tmp_db):
            if os.path.exists(f):
                os.remove(f)

    def tearDown(self):
        for f in (self.tmp_config, self.tmp_db):
            if os.path.exists(f):
                os.remove(f)

    @patch("src.ui.main_window.DesktopNotifier.notify_update")
    def test_handle_update_result_triggers_banner_tray_and_notif(self, mock_notify):
        from src.ui.main_window import MainWindow
        from src.providers.mock_provider import MockProvider

        cm = ConfigManager(custom_path=self.tmp_config)
        cm.config.jira_enabled = False
        provider = MockProvider()

        window = MainWindow(config_manager=cm, icon_path="", provider=provider)
        window.db = DatabaseManager(custom_path=self.tmp_db)

        info = UpdateInfo(
            available=True,
            current_commit="aaaaaaa",
            remote_commit="bbbbbbb",
            branch="main",
            commits_behind=1,
            changelog=["feat: nova feature (bbbbbbb)"]
        )

        window._handle_update_result(info)

        # Banner deve estar com visibilidade ativada (não hidden)
        self.assertFalse(window.update_banner.isHidden())
        # Ação no tray deve estar visível
        self.assertTrue(window.tray.update_action.isVisible())
        # Notificação desktop deve ter sido chamada
        mock_notify.assert_called_once()
        # Notificação deve ter sido gravada no banco
        notifs = window.db.get_active_notifications()
        self.assertTrue(any(n.item_type == "update" for n in notifs))


if __name__ == "__main__":
    unittest.main()

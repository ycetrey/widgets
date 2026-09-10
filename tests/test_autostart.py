"""
Testes unitários para o AutostartManager (Debian/GNOME XDG Autostart).
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.autostart import AutostartManager


class TestAutostartManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_home = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_autostart_path_respects_xdg(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.config_home)}):
            path = AutostartManager.get_autostart_path()
            expected = self.config_home / "autostart" / "dev-status-widget.desktop"
            self.assertEqual(path, expected)

    def test_enable_and_disable_autostart(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.config_home)}):
            # Inicialmente não está ativo
            self.assertFalse(AutostartManager.is_enabled())

            # Ativa autostart
            success = AutostartManager.set_enabled(True, exec_path="/usr/local/bin/dev-status-widget")
            self.assertTrue(success)
            self.assertTrue(AutostartManager.is_enabled())

            desktop_file = AutostartManager.get_autostart_path()
            self.assertTrue(desktop_file.exists())
            content = desktop_file.read_text(encoding="utf-8")
            self.assertIn("[Desktop Entry]", content)
            self.assertIn("dev-status-widget --minimized", content)
            self.assertIn("X-GNOME-Autostart-enabled=true", content)

            # Desativa autostart
            success_disable = AutostartManager.set_enabled(False)
            self.assertTrue(success_disable)
            self.assertFalse(AutostartManager.is_enabled())
            self.assertFalse(desktop_file.exists())


if __name__ == "__main__":
    unittest.main()

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

    @patch("sys.platform", "win32")
    def test_windows_autostart_workflow(self):
        fake_registry = {}

        class FakeKey:
            def __init__(self, root, subkey):
                self.root = root
                self.subkey = subkey

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        class FakeWinreg:
            HKEY_CURRENT_USER = "HKCU"
            KEY_READ = 1
            KEY_SET_VALUE = 2
            REG_SZ = 1

            @classmethod
            def OpenKey(cls, root, subkey, reserved, access):
                return FakeKey(root, subkey)

            @classmethod
            def QueryValueEx(cls, key, name):
                if name in fake_registry:
                    return (fake_registry[name], 1)
                raise FileNotFoundError()

            @classmethod
            def SetValueEx(cls, key, name, reserved, reg_type, value):
                fake_registry[name] = value

            @classmethod
            def DeleteValue(cls, key, name):
                if name in fake_registry:
                    del fake_registry[name]
                else:
                    raise FileNotFoundError()

        with patch.dict("sys.modules", {"winreg": FakeWinreg}):
            self.assertFalse(AutostartManager.is_enabled())

            success = AutostartManager.set_enabled(True, exec_path="C:\\app\\run.bat")
            self.assertTrue(success)
            self.assertTrue(AutostartManager.is_enabled())
            self.assertIn("DevStatusWidget", fake_registry)
            self.assertIn("C:\\app\\run.bat", fake_registry["DevStatusWidget"])

            success_disable = AutostartManager.set_enabled(False)
            self.assertTrue(success_disable)
            self.assertFalse(AutostartManager.is_enabled())
            self.assertNotIn("DevStatusWidget", fake_registry)


if __name__ == "__main__":
    unittest.main()

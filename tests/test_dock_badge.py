"""
Testes unitários para o gerenciador de badge no Dock do GNOME (DockBadgeManager).
"""
import unittest
from unittest.mock import MagicMock, patch

from src.ui.dock_badge import DockBadgeManager


class TestDockBadgeManager(unittest.TestCase):
    def setUp(self):
        self.badge_manager = DockBadgeManager("dev-status-widget.desktop")

    def test_initialization_desktop_extension(self):
        # Garante que a extensão .desktop é preservada ou adicionada
        mgr1 = DockBadgeManager("dev-status-widget.desktop")
        self.assertEqual(mgr1.desktop_app_id, "dev-status-widget.desktop")
        self.assertEqual(mgr1.app_uri, "application://dev-status-widget.desktop")

        mgr2 = DockBadgeManager("dev-status-widget")
        self.assertEqual(mgr2.desktop_app_id, "dev-status-widget.desktop")
        self.assertEqual(mgr2.app_uri, "application://dev-status-widget.desktop")

    def test_set_count_positive(self):
        # Testa atualização para contagem positiva
        res = self.badge_manager.set_count(5)
        self.assertEqual(self.badge_manager._current_count, 5)
        if self.badge_manager.is_available:
            self.assertTrue(res)

    def test_set_count_zero_and_negative(self):
        # Contagem zero deve ser 0
        self.badge_manager.set_count(0)
        self.assertEqual(self.badge_manager._current_count, 0)

        # Contagem negativa deve ser normalizada para 0
        self.badge_manager.set_count(-3)
        self.assertEqual(self.badge_manager._current_count, 0)

    def test_clear(self):
        self.badge_manager.set_count(8)
        self.assertEqual(self.badge_manager._current_count, 8)

        self.badge_manager.clear()
        self.assertEqual(self.badge_manager._current_count, 0)

    def test_dbus_message_structure(self):
        # Testa chamada simulada de envio D-Bus
        mock_bus = MagicMock()
        mock_bus.isConnected.return_value = True
        mock_bus.send.return_value = True

        self.badge_manager._bus = mock_bus

        res = self.badge_manager.set_count(10, urgent=True)
        self.assertTrue(res)
        self.assertTrue(mock_bus.send.called)

        # Verifica argumentos da mensagem enviada
        sent_msg = mock_bus.send.call_args[0][0]
        args = sent_msg.arguments()
        self.assertEqual(args[0], "application://dev-status-widget.desktop")
        self.assertEqual(args[1]["count"], 10)
        self.assertEqual(args[1]["count-visible"], True)
        self.assertEqual(args[1]["urgent"], True)

    def test_dbus_not_available_graceful_fallback(self):
        # Testa comportamento seguro quando o D-Bus não está disponível
        self.badge_manager._bus = None
        self.assertFalse(self.badge_manager.is_available)

        res = self.badge_manager.set_count(3)
        self.assertFalse(res)
        self.assertEqual(self.badge_manager._current_count, 3)

        res_clear = self.badge_manager.clear()
        self.assertFalse(res_clear)
        self.assertEqual(self.badge_manager._current_count, 0)


if __name__ == "__main__":
    unittest.main()

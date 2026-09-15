"""
Gerenciador do Contador / Badge no Dock do GNOME (Ubuntu Dock / Dash to Dock).
Integração nativa via D-Bus utilizando a especificação com.canonical.Unity.LauncherEntry.
"""
import os
from typing import Optional

try:
    from PyQt6.QtDBus import QDBusConnection, QDBusMessage
    HAS_QT_DBUS = True
except ImportError:
    HAS_QT_DBUS = False


class DockBadgeManager:
    """Gerencia o badge numérico no ícone da aplicação no Dock do GNOME."""

    INTERFACE = "com.canonical.Unity.LauncherEntry"
    SIGNAL = "Update"

    def __init__(self, desktop_app_id: str = "dev-status-widget.desktop"):
        if not desktop_app_id.endswith(".desktop"):
            desktop_app_id = f"{desktop_app_id}.desktop"
        self.desktop_app_id = desktop_app_id
        self.app_uri = f"application://{self.desktop_app_id}"
        self.path = f"/com/canonical/unity/launcherentry/{os.getpid()}"
        self._current_count = 0
        self._bus: Optional[QDBusConnection] = None

        if HAS_QT_DBUS:
            try:
                self._bus = QDBusConnection.sessionBus()
            except Exception as e:
                print(f"[DockBadge] Erro ao conectar ao D-Bus de sessão: {e}")

    @property
    def is_available(self) -> bool:
        return self._bus is not None and self._bus.isConnected()

    def set_count(self, count: int, urgent: bool = False) -> bool:
        """Atualiza a contagem exibida no badge do dock."""
        self._current_count = max(0, count)

        if not self.is_available:
            return False

        try:
            msg = QDBusMessage.createSignal(self.path, self.INTERFACE, self.SIGNAL)
            props = {
                "count": self._current_count,
                "count-visible": self._current_count > 0,
                "urgent": urgent,
            }
            msg.setArguments([self.app_uri, props])
            return self._bus.send(msg)
        except Exception as e:
            print(f"[DockBadge] Erro ao emitir sinal de badge para o D-Bus: {e}")
            return False

    def clear(self) -> bool:
        """Remove o badge do ícone no dock."""
        return self.set_count(0, urgent=False)

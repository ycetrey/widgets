"""
Gerenciador de notificações desktop para Linux (GNOME/Debian) e outras plataformas.
"""
import os
import shutil
import subprocess
import sys
import time
from typing import List, Optional
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QSystemTrayIcon


class DesktopNotifier:
    def __init__(
        self,
        tray_icon: Optional[QSystemTrayIcon] = None,
        icon_path: Optional[str] = None,
        sound_path: Optional[str] = None,
        sound_enabled: bool = True,
    ):
        self.tray_icon = tray_icon
        self.icon_path = os.path.abspath(icon_path) if icon_path else ""
        self.sound_path = os.path.abspath(sound_path) if sound_path else ""
        self.sound_enabled = sound_enabled
        self._last_sound_time = 0.0
        self._notify_send_available = (shutil.which("notify-send") is not None) if sys.platform != "win32" else False

        self._sound_effect: Optional[QSoundEffect] = None
        if self.sound_path and os.path.exists(self.sound_path):
            try:
                self._sound_effect = QSoundEffect()
                self._sound_effect.setSource(QUrl.fromLocalFile(self.sound_path))
                self._sound_effect.setVolume(0.85)
            except Exception as e:
                print(f"[Notifier] Erro ao carregar som de notificação: {e}")

    def set_tray_icon(self, tray_icon: QSystemTrayIcon):
        self.tray_icon = tray_icon

    def set_sound_enabled(self, enabled: bool):
        self.sound_enabled = enabled

    def play_sound(self, force: bool = False):
        """
        Reproduz o som de notificação (estilo WhatsApp) de forma assíncrona.
        Possui debounce de 1 segundo para evitar sobreposição em disparos em lote.
        """
        if not self.sound_enabled:
            return

        now = time.time()
        if not force and (now - self._last_sound_time < 1.0):
            return
        self._last_sound_time = now

        # 1. Tenta via QSoundEffect (nativa, assíncrona e baixa latência)
        if self._sound_effect is not None:
            try:
                self._sound_effect.play()
                return
            except Exception as e:
                print(f"[Notifier] Erro ao reproduzir via QSoundEffect: {e}")

        # 2. Fallback para Windows (winsound nativo)
        if sys.platform == "win32" and self.sound_path and os.path.exists(self.sound_path):
            try:
                import winsound
                winsound.PlaySound(self.sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except Exception as e:
                print(f"[Notifier] Erro ao reproduzir via winsound: {e}")

        # 3. Fallback para utilitários do sistema Linux
        if self.sound_path and os.path.exists(self.sound_path):
            for player in ["pw-play", "canberra-gtk-play", "aplay"]:
                if shutil.which(player):
                    try:
                        args = (
                            [player, "-f", self.sound_path]
                            if player == "canberra-gtk-play"
                            else [player, "-q", self.sound_path]
                            if player == "aplay"
                            else [player, self.sound_path]
                        )
                        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return
                    except Exception:
                        pass

    def notify(self, title: str, message: str, urgency: str = "normal", play_sound: bool = True):
        """
        Dispara uma notificação nativa para o usuário com o ícone do aplicativo e som.
        Tenta primeiro via notify-send (padrão GNOME/Debian com ícone oficial),
        e usa QSystemTrayIcon com QIcon como fallback elegante.
        """
        if play_sound:
            self.play_sound()
        sent_via_cmd = False
        if self._notify_send_available:
            try:
                cmd = ["notify-send", "-a", "Dev Status Widget", "-u", urgency]
                if self.icon_path and os.path.exists(self.icon_path):
                    cmd.extend(["-i", self.icon_path])
                cmd.extend([title, message])
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                sent_via_cmd = True
            except Exception as e:
                print(f"[Notifier] Erro ao chamar notify-send: {e}")

        # Fallback para o QSystemTrayIcon com o ícone customizado se notify-send não estiver disponível
        if not sent_via_cmd and self.tray_icon and self.tray_icon.isSystemTrayAvailable():
            try:
                if self.icon_path and os.path.exists(self.icon_path):
                    icon_arg = QIcon(self.icon_path)
                else:
                    icon_arg = QSystemTrayIcon.MessageIcon.Information if urgency != "critical" else QSystemTrayIcon.MessageIcon.Warning
                self.tray_icon.showMessage(title, message, icon_arg, 6000)
            except Exception as e:
                print(f"[Notifier] Erro ao enviar mensagem pelo tray: {e}")

    def notify_new_prs(self, new_prs: List):
        """
        Emite notificações elegantes para novas PRs detectadas.
        Se forem até 2 PRs, emite individualmente.
        Se forem mais, emite um resumo unificado para não poluir a tela do usuário.
        """
        if not new_prs:
            return

        if len(new_prs) <= 2:
            for pr in new_prs:
                title = f"Nova PR em {pr.repo}"
                msg = f"#{pr.number}: {pr.title}\npor @{pr.author}"
                self.notify(title, msg, urgency="normal")
        else:
            title = f"Novas Pull Requests ({len(new_prs)})"
            repos = set(pr.repo for pr in new_prs)
            repos_str = ", ".join(list(repos)[:3])
            msg = f"{len(new_prs)} novas PRs abertas em: {repos_str}"
            self.notify(title, msg, urgency="normal")

    def notify_new_jira_tasks(self, new_tasks: List):
        """
        Emite notificações elegantes para novas tarefas atribuídas no Jira.
        """
        if not new_tasks:
            return

        if len(new_tasks) <= 2:
            for task in new_tasks:
                title = f"Nova Tarefa Jira: {task.key}"
                msg = f"{task.summary}\nStatus: {task.status} | Prioridade: {task.priority}"
                self.notify(title, msg, urgency="normal")
        else:
            title = f"Novas Tarefas no Jira ({len(new_tasks)})"
            keys_str = ", ".join(t.key for t in new_tasks[:4])
            msg = f"{len(new_tasks)} novas tarefas atribuídas a você: {keys_str}..."
            self.notify(title, msg, urgency="normal")

    def notify_update(self, update_info, on_update_callback=None):
        """
        Dispara notificação nativa avisando sobre nova versão do Dev Status Widget no GitHub.
        Se suportado pelo sistema, adiciona botão de ação interativo para atualizar e reiniciar.
        """
        commits_str = f"{update_info.commits_behind} novo(s) commit(s)" if update_info.commits_behind > 0 else "novos commits"
        title = "🚀 Atualização Disponível!"
        message = f"Há {commits_str} no GitHub (branch {update_info.branch}).\nClique para atualizar e reiniciar."
        self.play_sound()

        if self._notify_send_available and on_update_callback:
            def _wait_action():
                try:
                    cmd = [
                        "notify-send",
                        "-a", "Dev Status Widget",
                        "-u", "normal",
                        "-A", "update=Atualizar e Reiniciar"
                    ]
                    if self.icon_path and os.path.exists(self.icon_path):
                        cmd.extend(["-i", self.icon_path])
                    cmd.extend([title, message])
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                    out, _ = proc.communicate(timeout=60)
                    if out and "update" in out.strip():
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(0, on_update_callback)
                except Exception as e:
                    print(f"[Notifier] Erro na notificação interativa de update: {e}")

            import threading
            threading.Thread(target=_wait_action, daemon=True).start()
        else:
            self.notify(title, message, urgency="normal")


"""
Gerenciador de notificações desktop para Linux (GNOME/Debian) e outras plataformas.
"""
import os
import shutil
import subprocess
from typing import List, Optional
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon


class DesktopNotifier:
    def __init__(self, tray_icon: Optional[QSystemTrayIcon] = None, icon_path: Optional[str] = None):
        self.tray_icon = tray_icon
        self.icon_path = os.path.abspath(icon_path) if icon_path else ""
        self._notify_send_available = shutil.which("notify-send") is not None

    def set_tray_icon(self, tray_icon: QSystemTrayIcon):
        self.tray_icon = tray_icon

    def notify(self, title: str, message: str, urgency: str = "normal"):
        """
        Dispara uma notificação nativa para o usuário com o ícone do aplicativo.
        Tenta primeiro via notify-send (padrão GNOME/Debian com ícone oficial),
        e usa QSystemTrayIcon com QIcon como fallback elegante.
        """
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


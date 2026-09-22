#!/usr/bin/env python3
"""
Ponto de entrada do Dev Status Widget.
Monitor de Pull Requests e Métricas para Linux Debian (GNOME).
"""
import argparse
import os
import signal
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.core.config import ConfigManager
from src.ui.main_window import MainWindow
from src.ui.theme import apply_theme


def parse_args():
    parser = argparse.ArgumentParser(description="Widget de Pull Requests e Métricas para Debian/GNOME")
    parser.add_argument("--config", "-c", help="Caminho para arquivo de configuração alternativo")
    parser.add_argument("--minimized", "-m", action="store_true", help="Inicia o aplicativo minimizado na bandeja")
    parser.add_argument("--demo", action="store_true", help="Inicia em modo de demonstração com PRs simuladas")
    parser.add_argument(
        "--dangerous-skip-permissions",
        "--dangerously-skip-permissions",
        action="store_true",
        dest="skip_permissions",
        help="Ignora diálogos de confirmação, avisos de segurança e checagens de permissão"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Permite que o sinal SIGINT (Ctrl+C) encerre o aplicativo no terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Configura AppUserModelID no Windows para que o ícone correto seja fixado na barra de tarefas
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("devwidgets.statuswidget.app.1")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("dev-status-widget")
    app.setApplicationDisplayName("Dev Status Widget")
    app.setOrganizationName("DevWidgets")
    app.setDesktopFileName("dev-status-widget")

    # Garante que o app não encerre se a última janela for fechada enquanto a bandeja estiver ativa
    app.setQuitOnLastWindowClosed(False)

    # Carrega configurações
    config_mgr = ConfigManager(custom_path=args.config)
    config = config_mgr.config
    if args.skip_permissions:
        config.skip_permissions = True
        print("[Aviso] Modo --dangerous-skip-permissions ativado: confirmações e checagens desativadas.")

    # Aplica tema escuro estilo moderno
    apply_theme(app, dark_mode=config.dark_mode)

    # Caminho do ícone
    base_dir = Path(__file__).resolve().parent
    icon_ico_path = str(base_dir / "assets" / "icon.ico")
    icon_path = str(base_dir / "assets" / "icon.png")
    favicon_path = str(base_dir / "assets" / "favicon-32.png")

    # Configura ícone da aplicação para Dock/Taskbar e janelas
    app_icon = QIcon()
    if os.path.exists(icon_ico_path):
        app_icon.addFile(icon_ico_path)
    if os.path.exists(icon_path):
        app_icon.addFile(icon_path)
    if os.path.exists(favicon_path):
        app_icon.addFile(favicon_path)
    app.setWindowIcon(app_icon)

    # Provedor customizado se estiver no modo demo
    provider = None
    jira_provider = None
    if args.demo:
        from src.providers.mock_provider import MockProvider
        from src.providers.jira_provider import JiraProvider
        provider = MockProvider(sort_order=config.sort_order)
        jira_provider = JiraProvider(demo_mode=True)
        print("[Demo] Iniciando aplicativo com dados de demonstração (GitHub e Jira).")

    # Cria janela principal
    window = MainWindow(config_manager=config_mgr, icon_path=icon_path, provider=provider, jira_provider=jira_provider)

    # Exibe ou mantém minimizado
    start_min = args.minimized or config.start_minimized
    if not start_min:
        window.show()

    # Timer curto para processar sinais do sistema (SIGINT)
    sig_timer = QTimer()
    sig_timer.start(500)
    sig_timer.timeout.connect(lambda: None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

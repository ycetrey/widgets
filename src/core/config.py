"""
Gerenciador de configurações para o aplicativo.
"""
import os
import yaml
from pathlib import Path
from typing import Optional
from .models import AppConfig


class ConfigManager:
    APP_DIR_NAME = "dev-status-widget"
    DEFAULT_FILENAME = "config.yaml"

    def __init__(self, custom_path: Optional[str] = None):
        self.custom_path = custom_path
        self._config_file = self._resolve_config_path()
        self.config: AppConfig = self.load()

    def _resolve_config_path(self) -> Path:
        if self.custom_path:
            return Path(self.custom_path)

        # 1. Checa no diretório local da aplicação
        local_config = Path(__file__).resolve().parent.parent.parent / self.DEFAULT_FILENAME
        if local_config.exists():
            return local_config

        # 2. Checa no diretório padrão XDG do Linux (~/.config/dev-status-widget/config.yaml)
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            user_config_dir = Path(xdg_config_home) / self.APP_DIR_NAME
        else:
            user_config_dir = Path.home() / ".config" / self.APP_DIR_NAME

        user_config_file = user_config_dir / self.DEFAULT_FILENAME
        if user_config_file.exists():
            return user_config_file

        # Se não existir em nenhum lugar, define o caminho do diretório de usuário para criação
        return user_config_file

    def load(self) -> AppConfig:
        if not self._config_file.exists():
            # Cria configuração padrão
            default_config = AppConfig(
                repositories=[
                    "facebook/react",
                    "golang/go"
                ]
            )
            self.save(default_config)
            return default_config

        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            return AppConfig(
                github_token=str(data.get("github_token") or "").strip(),
                repositories=[str(r).strip() for r in data.get("repositories", []) if str(r).strip()],
                refresh_interval_minutes=int(data.get("refresh_interval_minutes", 5)),
                sort_order=str(data.get("sort_order", "oldest_first")),
                notifications_enabled=bool(data.get("notifications_enabled", True)),
                minimize_to_tray_on_close=bool(data.get("minimize_to_tray_on_close", True)),
                start_minimized=bool(data.get("start_minimized", False)),
                dark_mode=bool(data.get("dark_mode", True)),
                skip_permissions=bool(data.get("skip_permissions", False)),
                jira_enabled=bool(data.get("jira_enabled", False)),
                jira_url=str(data.get("jira_url") or "").strip(),
                jira_email=str(data.get("jira_email") or "").strip(),
                jira_api_token=str(data.get("jira_api_token") or "").strip(),
                jira_jql=str(data.get("jira_jql") or "sprint in openSprints() AND (assignee = currentUser() OR assignee is EMPTY) ORDER BY updated DESC").strip(),
                autostart=bool(data.get("autostart", False))
            )
        except Exception as e:
            print(f"Erro ao carregar configuração ({self._config_file}): {e}. Usando padrões.")
            return AppConfig()

    def save(self, config: Optional[AppConfig] = None) -> bool:
        if config is not None:
            self.config = config

        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "github_token": self.config.github_token,
                "repositories": self.config.repositories,
                "refresh_interval_minutes": self.config.refresh_interval_minutes,
                "sort_order": self.config.sort_order,
                "notifications_enabled": self.config.notifications_enabled,
                "minimize_to_tray_on_close": self.config.minimize_to_tray_on_close,
                "start_minimized": self.config.start_minimized,
                "dark_mode": self.config.dark_mode,
                "jira_enabled": self.config.jira_enabled,
                "jira_url": self.config.jira_url,
                "jira_email": self.config.jira_email,
                "jira_api_token": self.config.jira_api_token,
                "jira_jql": self.config.jira_jql,
                "autostart": self.config.autostart
            }
            with open(self._config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração ({self._config_file}): {e}")
            return False

    @property
    def config_path(self) -> Path:
        return self._config_file

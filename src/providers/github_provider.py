"""
Provedor de Pull Requests do GitHub.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Set
import requests

from ..core.models import PullRequestItem
from .base import BaseStatusProvider


class GitHubProvider(BaseStatusProvider):
    API_BASE = "https://api.github.com"

    def __init__(self, token: str = "", repositories: List[str] = None, sort_order: str = "oldest_first"):
        self.token = token.strip() if token else ""
        self.repositories = repositories or []
        self.sort_order = sort_order
        self._known_pr_urls: Set[str] = set()
        self._is_first_run: bool = True

    def update_config(self, token: str, repositories: List[str], sort_order: str = "oldest_first"):
        self.token = token.strip() if token else ""
        self.repositories = repositories
        self.sort_order = sort_order

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DevStatusWidget-Debian/1.0"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _parse_datetime(self, iso_str: str) -> datetime:
        if not iso_str:
            return datetime.now(timezone.utc)
        clean_str = iso_str.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean_str)
        except Exception:
            return datetime.now(timezone.utc)

    def fetch(self) -> Dict[str, Any]:
        """
        Coleta as PRs abertas de todos os repositórios configurados.
        Retorna dicionário com:
        - items: List[PullRequestItem] (ordenados)
        - new_items: List[PullRequestItem] (apenas novas PRs desde o ciclo anterior)
        - errors: List[str] (se algum repo falhou)
        """
        all_prs: List[PullRequestItem] = []
        errors: List[str] = []
        headers = self._get_headers()

        if not self.repositories:
            return {
                "items": [],
                "new_items": [],
                "errors": ["Nenhum repositório configurado."]
            }

        for repo in self.repositories:
            repo_clean = repo.strip()
            if not repo_clean or "/" not in repo_clean:
                continue

            url = f"{self.API_BASE}/repos/{repo_clean}/pulls"
            params = {
                "state": "open",
                "per_page": 100,
                "sort": "created",
                "direction": "asc"  # Solicita da mais antiga para a mais recente
            }

            try:
                response = requests.get(url, headers=headers, params=params, timeout=12)

                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        pr = PullRequestItem(
                            id=item.get("id", 0),
                            number=item.get("number", 0),
                            title=item.get("title", "Sem título"),
                            repo=repo_clean,
                            author=item.get("user", {}).get("login", "desconhecido"),
                            author_avatar=item.get("user", {}).get("avatar_url", ""),
                            html_url=item.get("html_url", ""),
                            created_at=self._parse_datetime(item.get("created_at")),
                            updated_at=self._parse_datetime(item.get("updated_at")),
                            is_draft=bool(item.get("draft", False)),
                            labels=[l.get("name", "") for l in item.get("labels", []) if isinstance(l, dict)],
                            comments_count=item.get("comments", 0)
                        )
                        all_prs.append(pr)
                elif response.status_code == 404:
                    errors.append(f"Repositório '{repo_clean}' não encontrado ou acesso restrito.")
                elif response.status_code == 401:
                    errors.append("Token do GitHub inválido ou expirado.")
                    break
                elif response.status_code == 403:
                    msg = "Limite de requisições da API atingido. Configure um GitHub Token nas opções."
                    errors.append(msg)
                    break
                else:
                    errors.append(f"Erro {response.status_code} ao consultar '{repo_clean}'.")
            except requests.exceptions.RequestException as e:
                errors.append(f"Falha de conexão com '{repo_clean}': {str(e)}")

        # Ordenação: da mais antiga para a mais recente (ou o contrário se configurado)
        reverse = (self.sort_order == "newest_first")
        all_prs.sort(key=lambda pr: pr.created_at, reverse=reverse)

        # Detecção de novas PRs para notificação
        current_urls = {pr.html_url for pr in all_prs}
        new_items: List[PullRequestItem] = []

        if self._is_first_run:
            # Na primeira execução após abrir o app, apenas registra as PRs existentes
            # para não disparar notificações em massa
            self._known_pr_urls = current_urls
            self._is_first_run = False
        else:
            # Em execuções subsequentes, identifica o que surgiu de novo
            for pr in all_prs:
                if pr.html_url not in self._known_pr_urls:
                    new_items.append(pr)
            # Atualiza o conjunto de conhecidos
            self._known_pr_urls = current_urls

        return {
            "items": all_prs,
            "new_items": new_items,
            "errors": errors
        }

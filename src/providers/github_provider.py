"""
Provedor de Pull Requests do GitHub.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import requests

from ..core.models import PullRequestItem
from .base import BaseStatusProvider


class GitHubProvider(BaseStatusProvider):
    API_BASE = "https://api.github.com"
    GRAPHQL_BASE = "https://api.github.com/graphql"

    def __init__(self, token: str = "", repositories: List[str] = None, sort_order: str = "oldest_first", github_username: str = ""):
        self.token = token.strip() if token else ""
        self.repositories = repositories or []
        self.sort_order = sort_order
        self.current_user = github_username.strip()
        self._known_pr_urls: Set[str] = set()
        self._is_first_run: bool = True

    def update_config(self, token: str, repositories: List[str], sort_order: str = "oldest_first", github_username: str = ""):
        self.token = token.strip() if token else ""
        self.repositories = repositories
        self.sort_order = sort_order
        if github_username:
            self.current_user = github_username.strip()

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

    def _fetch_repo_graphql(self, repo_clean: str, headers: Dict[str, str]) -> Optional[List[PullRequestItem]]:
        """Busca PRs com status de revisão via GitHub GraphQL API em lote."""
        if "/" not in repo_clean:
            return None
        owner, name = repo_clean.split("/", 1)
        query = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            pullRequests(first: 100, states: OPEN, orderBy: {field: CREATED_AT, direction: ASC}) {
              nodes {
                databaseId
                number
                title
                url
                createdAt
                updatedAt
                isDraft
                reviewDecision
                author {
                  login
                  avatarUrl
                }
                labels(first: 10) {
                  nodes {
                    name
                  }
                }
                totalCommentsCount
                commits(last: 1) {
                  nodes {
                    commit {
                      statusCheckRollup {
                        state
                        contexts(first: 50) {
                          totalCount
                          nodes {
                            ... on CheckRun {
                              conclusion
                              status
                            }
                            ... on StatusContext {
                              state
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        response = requests.post(
            self.GRAPHQL_BASE,
            headers=headers,
            json={"query": query, "variables": {"owner": owner, "name": name}},
            timeout=12
        )
        if response.status_code == 200:
            data = response.json()
            if "errors" in data and not data.get("data", {}).get("repository"):
                return None
            repo_data = data.get("data", {}).get("repository")
            if not repo_data:
                return None
            nodes = repo_data.get("pullRequests", {}).get("nodes", [])
            prs: List[PullRequestItem] = []
            for item in nodes:
                author_obj = item.get("author") or {}
                labels_nodes = (item.get("labels") or {}).get("nodes", [])
                labels = [l.get("name", "") for l in labels_nodes if isinstance(l, dict) and l.get("name")]

                checks_summary = None
                checks_state = None
                commits_nodes = (item.get("commits") or {}).get("nodes", [])
                if commits_nodes:
                    commit_obj = commits_nodes[0].get("commit") or {}
                    rollup = commit_obj.get("statusCheckRollup") or {}
                    if rollup:
                        checks_state = rollup.get("state")
                        contexts = rollup.get("contexts") or {}
                        total = contexts.get("totalCount", 0)
                        if total > 0:
                            c_nodes = contexts.get("nodes", [])
                            success_count = sum(
                                1 for c in c_nodes
                                if (c.get("conclusion") or "").upper() == "SUCCESS" or (c.get("state") or "").upper() == "SUCCESS"
                            )
                            checks_summary = f"{success_count}/{total}"

                pr = PullRequestItem(
                    id=item.get("databaseId") or item.get("number", 0),
                    number=item.get("number", 0),
                    title=item.get("title", "Sem título"),
                    repo=repo_clean,
                    author=author_obj.get("login", "desconhecido"),
                    author_avatar=author_obj.get("avatarUrl", ""),
                    html_url=item.get("url", ""),
                    created_at=self._parse_datetime(item.get("createdAt")),
                    updated_at=self._parse_datetime(item.get("updatedAt")),
                    is_draft=bool(item.get("isDraft", False)),
                    labels=labels,
                    comments_count=item.get("totalCommentsCount", 0),
                    review_decision=item.get("reviewDecision"),
                    checks_summary=checks_summary,
                    checks_state=checks_state
                )
                prs.append(pr)
            return prs
        return None

    def _fetch_repo_rest(self, repo_clean: str, headers: Dict[str, str]) -> tuple[List[PullRequestItem], Optional[str]]:
        """Busca PRs via GitHub REST API tradicional."""
        url = f"{self.API_BASE}/repos/{repo_clean}/pulls"
        params = {
            "state": "open",
            "per_page": 100,
            "sort": "created",
            "direction": "asc"
        }
        prs: List[PullRequestItem] = []
        try:
            response = requests.get(url, headers=headers, params=params, timeout=12)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    has_reviewers = bool(item.get("requested_reviewers") or item.get("requested_teams"))
                    review_dec = "REVIEW_REQUIRED" if has_reviewers else None
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
                        comments_count=item.get("comments", 0),
                        review_decision=review_dec
                    )
                    prs.append(pr)
                return prs, None
            elif response.status_code == 404:
                return [], f"Repositório '{repo_clean}' não encontrado ou acesso restrito."
            elif response.status_code == 401:
                return [], "Token do GitHub inválido ou expirado."
            elif response.status_code == 403:
                return [], "Limite de requisições da API atingido. Configure um GitHub Token nas opções."
            else:
                return [], f"Erro {response.status_code} ao consultar '{repo_clean}'."
        except requests.exceptions.RequestException as e:
            return [], f"Falha de conexão com '{repo_clean}': {str(e)}"

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

            repo_prs: Optional[List[PullRequestItem]] = None

            # Tenta via GraphQL quando houver token configurado
            if self.token:
                try:
                    repo_prs = self._fetch_repo_graphql(repo_clean, headers)
                except Exception:
                    repo_prs = None

            # Fallback para REST se GraphQL não retornou ou se não houver token
            if repo_prs is None:
                prs, err = self._fetch_repo_rest(repo_clean, headers)
                if err:
                    errors.append(err)
                    if "Token do GitHub inválido" in err or "Limite de requisições" in err:
                        break
                all_prs.extend(prs)
            else:
                all_prs.extend(repo_prs)

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

        if not self.current_user and self.token:
            try:
                user_res = requests.get(f"{self.API_BASE}/user", headers=headers, timeout=5)
                if user_res.status_code == 200:
                    self.current_user = user_res.json().get("login", "")
            except Exception:
                pass

        return {
            "items": all_prs,
            "new_items": new_items,
            "errors": errors,
            "current_user": self.current_user
        }

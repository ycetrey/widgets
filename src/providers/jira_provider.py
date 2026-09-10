"""
Provedor de Tarefas do Atlassian Jira via API REST.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
import requests
from requests.auth import HTTPBasicAuth

from ..core.models import JiraTaskItem
from .base import BaseStatusProvider


class JiraProvider(BaseStatusProvider):
    DEFAULT_JQL = "sprint in openSprints() AND (assignee = currentUser() OR assignee is EMPTY) ORDER BY updated DESC"

    def __init__(
        self,
        jira_url: str = "",
        email: str = "",
        api_token: str = "",
        jql: str = DEFAULT_JQL,
        demo_mode: bool = False
    ):
        self.jira_url = jira_url.strip().rstrip("/") if jira_url else ""
        self.email = email.strip() if email else ""
        self.api_token = api_token.strip() if api_token else ""
        self.jql = jql.strip() if jql else self.DEFAULT_JQL
        self.demo_mode = demo_mode
        self._known_keys: Set[str] = set()
        self._is_first_run: bool = True
        self._demo_cycle: int = 0

    def update_config(self, jira_url: str, email: str, api_token: str, jql: str):
        self.jira_url = jira_url.strip().rstrip("/") if jira_url else ""
        self.email = email.strip() if email else ""
        self.api_token = api_token.strip() if api_token else ""
        if jql:
            self.jql = jql.strip()

    def _parse_datetime(self, iso_str: str) -> datetime:
        if not iso_str:
            return datetime.now(timezone.utc)
        clean = iso_str.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean)
        except Exception:
            return datetime.now(timezone.utc)

    def fetch(self) -> Dict[str, Any]:
        """
        Consulta as tarefas do Jira.
        Se em modo demo ou se credenciais não forem fornecidas, retorna dados simulados.
        """
        if self.demo_mode or not (self.jira_url and self.email and self.api_token):
            return self._fetch_mock_data()

        headers = {
            "Accept": "application/json",
            "User-Agent": "DevStatusWidget-Debian/1.0"
        }
        auth = HTTPBasicAuth(self.email, self.api_token)

        # Jira Cloud migrou a busca JQL para /rest/api/3/search/jql (CHANGE-2046)
        # Endpoints antigos (/rest/api/3/search e /rest/api/2/search) retornam HTTP 410 Gone no Jira Cloud.
        endpoint = f"{self.jira_url}/rest/api/3/search/jql"
        params = {
            "jql": self.jql,
            "fields": "summary,status,priority,issuetype,assignee,created,updated,parent",
            "maxResults": 100
        }

        try:
            resp = requests.get(endpoint, headers=headers, auth=auth, params=params, timeout=12)

            # Fallback para instâncias Jira Server / Data Center locais que ainda utilizam v3 ou v2
            if resp.status_code in (404, 405):
                endpoint = f"{self.jira_url}/rest/api/3/search"
                resp = requests.get(endpoint, headers=headers, auth=auth, params=params, timeout=12)
                if resp.status_code in (404, 410):
                    endpoint = f"{self.jira_url}/rest/api/2/search"
                    resp = requests.get(endpoint, headers=headers, auth=auth, params=params, timeout=12)

            if resp.status_code == 200:
                data = resp.json()
                issues = data.get("issues", [])
                items: List[JiraTaskItem] = []

                for issue in issues:
                    fields = issue.get("fields") or {}
                    key = issue.get("key", "JIRA-0")
                    status_obj = fields.get("status") or {}
                    status_name = status_obj.get("name", "Desconhecido")
                    status_cat = (status_obj.get("statusCategory") or {}).get("key", "new")

                    priority_obj = fields.get("priority") or {}
                    priority_name = priority_obj.get("name", "Normal")

                    type_obj = fields.get("issuetype") or {}
                    type_name = type_obj.get("name", "Tarefa")

                    assignee_obj = fields.get("assignee") or {}
                    assignee_name = assignee_obj.get("displayName") or "Não atribuído"
                    assignee_avatar = ((assignee_obj.get("avatarUrls") or {}).get("48x48")) or ""

                    parent_obj = fields.get("parent") or {}
                    parent_key = parent_obj.get("key")
                    parent_fields = parent_obj.get("fields") or {}
                    parent_summary = parent_fields.get("summary")
                    parent_status = (parent_fields.get("status") or {}).get("name")
                    parent_issue_type = (parent_fields.get("issuetype") or {}).get("name")

                    created_dt = self._parse_datetime(fields.get("created"))
                    updated_dt = self._parse_datetime(fields.get("updated"))
                    html_url = f"{self.jira_url}/browse/{key}"

                    item = JiraTaskItem(
                        key=key,
                        summary=fields.get("summary", "Sem resumo"),
                        status=status_name,
                        status_category=status_cat,
                        priority=priority_name,
                        issue_type=type_name,
                        assignee=assignee_name,
                        created_at=created_dt,
                        updated_at=updated_dt,
                        html_url=html_url,
                        assignee_avatar=assignee_avatar,
                        parent_key=parent_key,
                        parent_summary=parent_summary,
                        parent_status=parent_status,
                        parent_issue_type=parent_issue_type
                    )
                    items.append(item)

                # Detecção de novas tarefas
                current_keys = {item.key for item in items}
                new_items: List[JiraTaskItem] = []

                if self._is_first_run:
                    self._known_keys = current_keys
                    self._is_first_run = False
                else:
                    for item in items:
                        if item.key not in self._known_keys:
                            new_items.append(item)
                    self._known_keys = current_keys

                return {
                    "items": items,
                    "new_items": new_items,
                    "errors": []
                }
            elif resp.status_code == 401:
                return {
                    "items": [],
                    "new_items": [],
                    "errors": ["Jira: Credenciais inválidas (E-mail ou API Token incorretos)."]
                }
            elif resp.status_code == 403:
                return {
                    "items": [],
                    "new_items": [],
                    "errors": ["Jira: Acesso negado. Verifique as permissões da conta ou token."]
                }
            elif resp.status_code == 400:
                err_detail = ""
                try:
                    err_json = resp.json()
                    msgs = err_json.get("errorMessages", [])
                    if msgs:
                        err_detail = f": {'; '.join(msgs)}"
                except Exception:
                    pass
                return {
                    "items": [],
                    "new_items": [],
                    "errors": [f"Jira: Consulta JQL inválida{err_detail}. Verifique a sintaxe nas configurações."]
                }
            else:
                return {
                    "items": [],
                    "new_items": [],
                    "errors": [f"Jira: Erro {resp.status_code} ao consultar tarefas."]
                }
        except requests.exceptions.RequestException as e:
            return {
                "items": [],
                "new_items": [],
                "errors": [f"Jira: Falha na conexão: {str(e)}"]
            }

    def _fetch_mock_data(self) -> Dict[str, Any]:
        """Gera tarefas fictícias para testes e modo de demonstração."""
        now = datetime.now(timezone.utc)
        self._demo_cycle += 1

        items: List[JiraTaskItem] = [
            JiraTaskItem(
                key="DEV-402",
                summary="Implementar autenticação OAuth2 e suporte a refresh tokens",
                status="Em Progresso",
                status_category="indeterminate",
                priority="Alta",
                issue_type="História",
                assignee="Você",
                created_at=now - timedelta(days=5),
                updated_at=now - timedelta(minutes=45),
                html_url="https://jira.example.com/browse/DEV-402"
            ),
            JiraTaskItem(
                key="DEV-388",
                summary="Investigar lentidão nas consultas de relatórios mensais",
                status="A Fazer",
                status_category="new",
                priority="Crítica",
                issue_type="Bug",
                assignee="Você",
                created_at=now - timedelta(days=8),
                updated_at=now - timedelta(hours=3),
                html_url="https://jira.example.com/browse/DEV-388"
            ),
            JiraTaskItem(
                key="DEV-350",
                summary="Criar documentação da API pública de webhooks",
                status="Em Revisão",
                status_category="indeterminate",
                priority="Média",
                issue_type="Tarefa",
                assignee="Você",
                created_at=now - timedelta(days=12),
                updated_at=now - timedelta(hours=6),
                html_url="https://jira.example.com/browse/DEV-350"
            ),
            JiraTaskItem(
                key="DEV-310",
                summary="Atualizar dependências de segurança do container Debian",
                status="Concluído",
                status_category="done",
                priority="Baixa",
                issue_type="Melhoria",
                assignee="Você",
                created_at=now - timedelta(days=20),
                updated_at=now - timedelta(days=1),
                html_url="https://jira.example.com/browse/DEV-310"
            )
        ]

        new_items = []
        if self._demo_cycle > 1:
            new_task = JiraTaskItem(
                key="DEV-415",
                summary="Nova tarefa urgente atribuída a você: Validação de deploy",
                status="A Fazer",
                status_category="new",
                priority="Crítica",
                issue_type="Bug",
                assignee="Você",
                created_at=now - timedelta(minutes=2),
                updated_at=now - timedelta(minutes=2),
                html_url="https://jira.example.com/browse/DEV-415"
            )
            items.insert(0, new_task)
            new_items.append(new_task)

        return {
            "items": items,
            "new_items": new_items,
            "errors": []
        }

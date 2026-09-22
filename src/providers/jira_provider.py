"""
Provedor de Tarefas do Atlassian Jira via API REST.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
import requests
from requests.auth import HTTPBasicAuth

from ..core.models import JiraSprintInfo, JiraTaskItem
from .base import BaseStatusProvider


class JiraProvider(BaseStatusProvider):
    DEFAULT_JQL = "sprint in openSprints() AND (assignee = currentUser() OR assignee is EMPTY) AND issuetype not in subtaskIssueTypes() ORDER BY updated DESC"

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
        self.current_user_name: Optional[str] = None
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
            "fields": "summary,status,priority,issuetype,assignee,created,updated,parent,subtasks",
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

                # 1. Identifica subtarefas filhas das histórias que não vieram na consulta inicial (ex: subtarefas de QA atribuídas a outro membro da equipe)
                all_subtask_keys = set()
                for issue in issues:
                    f = issue.get("fields") or {}
                    for st in f.get("subtasks") or []:
                        st_k = st.get("key")
                        if st_k:
                            all_subtask_keys.add(st_k)

                existing_keys = {i.get("key") for i in issues}
                missing_subtask_keys = [k for k in all_subtask_keys if k not in existing_keys]

                # 2. Busca em lote os detalhes reais (incluindo o assignee real, ex: QA 'Nicolle Emanuele')
                if missing_subtask_keys:
                    try:
                        for chunk_start in range(0, len(missing_subtask_keys), 50):
                            chunk_keys = missing_subtask_keys[chunk_start:chunk_start + 50]
                            chunk_jql = f"key in ({','.join(chunk_keys)})"
                            batch_params = {
                                "jql": chunk_jql,
                                "fields": "summary,status,priority,issuetype,assignee,created,updated,parent",
                                "maxResults": len(chunk_keys)
                            }
                            b_resp = requests.get(endpoint, headers=headers, auth=auth, params=batch_params, timeout=10)
                            if b_resp.status_code == 200:
                                b_data = b_resp.json()
                                issues.extend(b_data.get("issues", []))
                    except Exception as e:
                        print(f"[Jira] Aviso: Erro ao buscar detalhes de subtarefas filhas ausentes: {e}")

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
                    is_subtask = type_obj.get("subtask", False)
                    hierarchy_level = type_obj.get("hierarchyLevel", -1 if is_subtask else 0)

                    assignee_obj = fields.get("assignee") or {}
                    assignee_name = assignee_obj.get("displayName") or "Não atribuído"
                    assignee_email = (assignee_obj.get("emailAddress") or "").strip().lower()
                    if self.email and assignee_email and assignee_email == self.email.lower():
                        self.current_user_name = assignee_name
                    assignee_avatar = ((assignee_obj.get("avatarUrls") or {}).get("48x48")) or ""

                    parent_obj = fields.get("parent") or {}
                    raw_parent_key = parent_obj.get("key")
                    parent_fields = parent_obj.get("fields") or {}
                    raw_parent_summary = parent_fields.get("summary")
                    raw_parent_status = (parent_fields.get("status") or {}).get("name")
                    parent_type_obj = parent_fields.get("issuetype") or {}
                    raw_parent_issue_type = parent_type_obj.get("name")
                    parent_hierarchy = parent_type_obj.get("hierarchyLevel")

                    # Distingue Épico de História Pai:
                    # Se o pai for do tipo 'Epic' (ou hierarchyLevel 1), ele é um Épico, não uma História/Swimlane
                    is_parent_epic = (
                        (raw_parent_issue_type and raw_parent_issue_type.lower() in ("epic", "épico")) or
                        parent_hierarchy == 1
                    )

                    epic_key = None
                    epic_summary = None
                    parent_key = None
                    parent_summary = None
                    parent_status = None
                    parent_issue_type = None

                    if is_parent_epic:
                        epic_key = raw_parent_key
                        epic_summary = raw_parent_summary
                        if is_subtask:
                            parent_key = raw_parent_key
                            parent_summary = raw_parent_summary
                            parent_status = raw_parent_status
                            parent_issue_type = raw_parent_issue_type
                    else:
                        if is_subtask:
                            parent_key = raw_parent_key
                            parent_summary = raw_parent_summary
                            parent_status = raw_parent_status
                            parent_issue_type = raw_parent_issue_type
                        elif raw_parent_key:
                            epic_key = raw_parent_key
                            epic_summary = raw_parent_summary

                    # Subtarefas anexadas à issue (quando esta for uma História/Tarefa)
                    raw_subtasks = fields.get("subtasks") or []
                    subtasks_list = []
                    for st in raw_subtasks:
                        st_fields = st.get("fields") or {}
                        st_status_obj = st_fields.get("status") or {}
                        st_prio_obj = st_fields.get("priority") or {}
                        st_type_obj = st_fields.get("issuetype") or {}
                        subtasks_list.append({
                            "key": st.get("key"),
                            "summary": st_fields.get("summary", ""),
                            "status": st_status_obj.get("name", "To Do"),
                            "status_category": (st_status_obj.get("statusCategory") or {}).get("key", "new"),
                            "priority": st_prio_obj.get("name", "Normal"),
                            "issue_type": st_type_obj.get("name", "Subtarefa"),
                        })

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
                        parent_issue_type=parent_issue_type,
                        is_subtask=is_subtask,
                        epic_key=epic_key,
                        epic_summary=epic_summary,
                        subtasks_list=subtasks_list
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
                    "errors": [],
                    "current_user_name": self.current_user_name
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

    def get_active_sprint(self, sample_task_key: str) -> Optional[JiraSprintInfo]:
        """
        Descobre a sprint ativa do board correspondente ao projeto de
        `sample_task_key` (ex: "FF-1234" -> projeto "FF") usando a API Agile
        do Jira. Retorna None se estiver em modo demo, faltar credenciais,
        ou não houver board/sprint ativa encontrados.
        """
        if self.demo_mode or not (self.jira_url and self.email and self.api_token):
            return None
        if not sample_task_key or "-" not in sample_task_key:
            return None

        project_key = sample_task_key.split("-", 1)[0]
        headers = {
            "Accept": "application/json",
            "User-Agent": "DevStatusWidget-Debian/1.0"
        }
        auth = HTTPBasicAuth(self.email, self.api_token)

        try:
            board_resp = requests.get(
                f"{self.jira_url}/rest/agile/1.0/board",
                headers=headers, auth=auth,
                params={"projectKeyOrId": project_key},
                timeout=12
            )
            if board_resp.status_code != 200:
                return None
            boards = board_resp.json().get("values", [])
            if not boards:
                return None
            board_id = boards[0]["id"]

            sprint_resp = requests.get(
                f"{self.jira_url}/rest/agile/1.0/board/{board_id}/sprint",
                headers=headers, auth=auth,
                params={"state": "active"},
                timeout=12
            )
            if sprint_resp.status_code != 200:
                return None
            sprints = sprint_resp.json().get("values", [])
            if not sprints:
                return None

            sprint = sprints[0]
            return JiraSprintInfo(
                id=sprint["id"],
                name=sprint.get("name", ""),
                start_date=self._parse_datetime(sprint["startDate"]) if sprint.get("startDate") else None,
                end_date=self._parse_datetime(sprint["endDate"]) if sprint.get("endDate") else None
            )
        except requests.exceptions.RequestException:
            return None

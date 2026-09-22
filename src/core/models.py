"""
Modelos de dados para o Widget de Status e Pull Requests.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple


@dataclass
class PullRequestItem:
    id: int
    number: int
    title: str
    repo: str
    author: str
    author_avatar: str
    html_url: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_draft: bool = False
    labels: List[str] = field(default_factory=list)
    comments_count: int = 0
    review_decision: Optional[str] = None
    checks_summary: Optional[str] = None
    checks_state: Optional[str] = None

    @property
    def status_key(self) -> str:
        """
        Retorna a chave única do status da PR:
        - 'draft': PR em rascunho
        - 'changes_requested': Alterações solicitadas na revisão
        - 'approved': PR aprovada
        - 'review_required': Aguardando revisão
        - 'open': Aberta sem pendências de revisão
        """
        if self.is_draft:
            return "draft"
        if self.review_decision == "CHANGES_REQUESTED":
            return "changes_requested"
        elif self.review_decision == "APPROVED":
            return "approved"
        elif self.review_decision == "REVIEW_REQUIRED":
            return "review_required"

        for label in self.labels:
            lbl_lower = label.lower()
            if any(k in lbl_lower for k in ("revisao", "review", "precisa-revisao", "aguardando-revisao")):
                return "review_required"

        return "open"

    @property
    def status_label(self) -> str:
        """Retorna o rótulo descritivo do status."""
        mapping = {
            "draft": "Rascunho",
            "changes_requested": "Mudanças Solicitadas",
            "approved": "Aprovada",
            "review_required": "Aguardando Revisão",
            "open": "Aberta",
        }
        return mapping.get(self.status_key, "Aberta")

    @property
    def status_display(self) -> str:
        """Retorna o rótulo formatado com emoji para cards e filtros."""
        mapping = {
            "draft": "📝 Rascunho",
            "changes_requested": "🔄 Mudanças Solicitadas",
            "approved": "✅ Aprovada",
            "review_required": "👀 Aguardando Revisão",
            "open": "🟢 Aberta",
        }
        return mapping.get(self.status_key, "🟢 Aberta")


    @property
    def age_days(self) -> float:
        now = datetime.now(timezone.utc)
        diff = now - self.created_at
        return diff.total_seconds() / 86400.0

    @property
    def age_humanized(self) -> str:
        now = datetime.now(timezone.utc)
        diff = now - self.created_at
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "há poucos segundos"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"há {minutes} min"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"há {hours} h"
        else:
            days = seconds // 86400
            if days == 1:
                return "há 1 dia"
            elif days < 30:
                return f"há {days} dias"
            elif days < 365:
                months = days // 30
                return f"há {months} {'mês' if months == 1 else 'meses'}"
            else:
                years = days // 365
                return f"há {years} {'ano' if years == 1 else 'anos'}"

    @property
    def urgency_level(self) -> str:
        """
        Retorna o nível de urgência com base no tempo de espera da PR:
        - 'critical' (>= 14 dias): PR esquecida ou bloqueada há muito tempo
        - 'warning' (>= 4 dias): PR aguardando revisão significativa
        - 'attention' (>= 1 dia): PR aberta há mais de 24h
        - 'fresh' (< 1 dia): PR recém-criada
        """
        days = self.age_days
        if days >= 14:
            return "critical"
        elif days >= 4:
            return "warning"
        elif days >= 1:
            return "attention"
        return "fresh"

    @staticmethod
    def _format_relative_time(dt: Optional[datetime]) -> str:
        if not dt:
            return ""
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = max(1, seconds // 60)
            return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"
        elif seconds < 86400:
            hours = max(1, seconds // 3600)
            return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
        elif seconds < 172800:
            return "yesterday"
        else:
            days = seconds // 86400
            if days < 30:
                return f"{days} days ago"
            elif days < 365:
                months = days // 30
                return f"{months} {'month' if months == 1 else 'months'} ago"
            else:
                years = days // 365
                return f"{years} {'year' if years == 1 else 'years'} ago"

    @property
    def opened_humanized(self) -> str:
        return self._format_relative_time(self.created_at)

    @property
    def updated_humanized(self) -> str:
        return self._format_relative_time(self.updated_at) if self.updated_at else ""

    @property
    def review_display_github(self) -> Optional[Tuple[str, str, str]]:
        """
        Retorna (texto, cor_hex, icone) no padrão GitHub:
        - ('Review required', '#d29922', '➖')
        - ('Approved', '#3fb950', '✔')
        - ('Changes requested', '#f85149', '❌')
        - ('Draft', '#7d8590', '📝')
        """
        if self.is_draft:
            return ("Draft", "#7d8590", "📝")
        if self.review_decision == "CHANGES_REQUESTED":
            return ("Changes requested", "#f85149", "❌")
        elif self.review_decision == "APPROVED":
            return ("Approved", "#3fb950", "✔")
        elif self.review_decision == "REVIEW_REQUIRED":
            return ("Review required", "#d29922", "➖")

        for label in self.labels:
            lbl_lower = label.lower()
            if any(k in lbl_lower for k in ("revisao", "review", "precisa-revisao", "aguardando-revisao")):
                return ("Review required", "#d29922", "➖")

        return None


@dataclass
class JiraTaskItem:
    key: str
    summary: str
    status: str
    status_category: str  # "new", "indeterminate", "done"
    priority: str
    issue_type: str
    assignee: str
    created_at: datetime
    updated_at: datetime
    html_url: str
    assignee_avatar: str = ""
    parent_key: Optional[str] = None
    parent_summary: Optional[str] = None
    parent_status: Optional[str] = None
    parent_issue_type: Optional[str] = None
    is_subtask: bool = False
    epic_key: Optional[str] = None
    epic_summary: Optional[str] = None
    subtasks_list: List[dict] = field(default_factory=list)

    @property
    def updated_humanized(self) -> str:
        now = datetime.now(timezone.utc)
        diff = now - self.updated_at
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "há poucos segundos"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"há {minutes} min"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"há {hours} h"
        else:
            days = seconds // 86400
            if days == 1:
                return "há 1 dia"
            elif days < 30:
                return f"há {days} dias"
            else:
                months = days // 30
                return f"há {months} {'mês' if months == 1 else 'meses'}"


@dataclass
class JiraSprintInfo:
    id: int
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class AppConfig:
    github_token: str = ""
    github_username: str = ""
    repositories: List[str] = field(default_factory=list)
    refresh_interval_minutes: int = 5
    sort_order: str = "oldest_first"  # "oldest_first" ou "newest_first"
    notifications_enabled: bool = True
    sound_enabled: bool = True
    minimize_to_tray_on_close: bool = True
    start_minimized: bool = False
    dark_mode: bool = True
    skip_permissions: bool = False

    # Jira Integration
    jira_enabled: bool = False
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_jql: str = "sprint in openSprints() AND (assignee = currentUser() OR assignee is EMPTY) AND issuetype not in subtaskIssueTypes() ORDER BY updated DESC"

    # Inicialização Automática no Sistema (Debian/Linux)
    autostart: bool = False

    # Relatório de Sprint Freeze
    freeze_reports_enabled: bool = False
    freeze_production_branch: str = "rc-prod"


@dataclass
class SprintFreezeTaskEntry:
    key: str
    summary: str
    assignee: str
    jira_status: str
    html_url: str
    diagnosis: str
    pr_url: Optional[str] = None


@dataclass
class SprintFreezeReport:
    id: int
    sprint_id: str
    sprint_name: str
    generated_at: datetime
    is_automatic: bool
    total_tasks: int
    promoted_count: int
    retained_count: int
    pdf_path: str
    retained_tasks: List[SprintFreezeTaskEntry] = field(default_factory=list)


@dataclass
class NotificationItem:
    id: int
    item_key: str
    item_type: str  # "pr", "jira", "system"
    title: str
    message: str
    link_url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_dismissed: bool = False

    @property
    def time_humanized(self) -> str:
        now = datetime.now(timezone.utc)
        diff = now - self.created_at
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "há poucos segundos"
        elif seconds < 3600:
            minutes = max(1, seconds // 60)
            return f"há {minutes} min"
        elif seconds < 86400:
            hours = max(1, seconds // 3600)
            return f"há {hours} h"
        else:
            days = seconds // 86400
            if days == 1:
                return "ontem"
            elif days < 30:
                return f"há {days} dias"
            else:
                months = days // 30
                return f"há {months} {'mês' if months == 1 else 'meses'}"


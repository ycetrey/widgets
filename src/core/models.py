"""
Modelos de dados para o Widget de Status e Pull Requests.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


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
class AppConfig:
    github_token: str = ""
    repositories: List[str] = field(default_factory=list)
    refresh_interval_minutes: int = 5
    sort_order: str = "oldest_first"  # "oldest_first" ou "newest_first"
    notifications_enabled: bool = True
    minimize_to_tray_on_close: bool = True
    start_minimized: bool = False
    dark_mode: bool = True
    skip_permissions: bool = False

    # Jira Integration
    jira_enabled: bool = False
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_jql: str = "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"


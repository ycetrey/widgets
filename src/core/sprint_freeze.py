"""
Serviço de geração do Relatório de Sprint Freeze: cruza tarefas do Jira com
PRs de promoção no GitHub para identificar o que não chegou em produção.
"""
from datetime import date, datetime, timezone
from typing import List, Optional

from .models import JiraSprintInfo, JiraTaskItem, SprintFreezeReport, SprintFreezeTaskEntry

STATUS_CATEGORY_EMOJI = {
    "new": "🔨",
    "indeterminate": "🧪",
    "done": "✅",
}


def build_report(
    jira_tasks: List[JiraTaskItem],
    sprint_info: JiraSprintInfo,
    promotion_status: dict,
    is_automatic: bool = False,
    github_search_failed: bool = False,
) -> SprintFreezeReport:
    """
    Monta o SprintFreezeReport a partir das tarefas da sprint (apenas as que
    não são subtarefas), da sprint ativa e do resultado de
    `GitHubProvider.search_promotion_prs()` (dict {chave: {"merged": bool, "pr_url": str}}).
    Se `github_search_failed=True`, tarefas sem PR encontrada recebem o
    diagnóstico "não foi possível verificar" em vez do status do Jira, para
    não conflitar "sem PR" com "falha ao consultar o GitHub".
    """
    top_level_tasks = [t for t in jira_tasks if not t.is_subtask]
    retained: List[SprintFreezeTaskEntry] = []
    promoted_count = 0

    for task in top_level_tasks:
        promo = promotion_status.get(task.key)

        if promo and promo.get("merged"):
            promoted_count += 1
            continue

        if promo and not promo.get("merged"):
            diagnosis = "⚠️ PR aberta aguardando merge"
            pr_url = promo.get("pr_url")
        elif github_search_failed:
            diagnosis = "❔ Não foi possível verificar PR"
            pr_url = None
        else:
            emoji = STATUS_CATEGORY_EMOJI.get(task.status_category, "🔎")
            diagnosis = f"{emoji} {task.status}"
            pr_url = None

        retained.append(SprintFreezeTaskEntry(
            key=task.key,
            summary=task.summary,
            assignee=task.assignee,
            jira_status=task.status,
            html_url=task.html_url,
            diagnosis=diagnosis,
            pr_url=pr_url
        ))

    return SprintFreezeReport(
        id=0,
        sprint_id=str(sprint_info.id),
        sprint_name=sprint_info.name,
        generated_at=datetime.now(timezone.utc),
        is_automatic=is_automatic,
        total_tasks=len(top_level_tasks),
        promoted_count=promoted_count,
        retained_count=len(retained),
        pdf_path="",
        retained_tasks=retained
    )


def should_generate_automatic_report(
    today: date,
    sprint_end_date: Optional[datetime],
    already_has_automatic: bool,
) -> bool:
    """
    Decide se a checagem automática de segunda-feira deve gerar um novo
    relatório: precisa ser segunda-feira, a sprint ativa precisa já ter
    passado da data de término, e ainda não pode existir um relatório
    automático para essa sprint.
    """
    if already_has_automatic:
        return False
    if today.weekday() != 0:
        return False
    if sprint_end_date is None:
        return False
    return sprint_end_date.date() <= today

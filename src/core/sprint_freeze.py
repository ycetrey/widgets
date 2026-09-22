"""
Serviço de geração do Relatório de Sprint Freeze: cruza tarefas do Jira com
PRs de promoção no GitHub para identificar o que não chegou em produção.
"""
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional

from .database import DatabaseManager
from .models import JiraSprintInfo, JiraTaskItem, SprintFreezeReport, SprintFreezeTaskEntry
from .pdf_report import render_report_pdf

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


def default_reports_dir() -> Path:
    """Diretório padrão de armazenamento dos PDFs, no mesmo padrão do banco SQLite."""
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        base_dir = (Path(localappdata) if localappdata else Path.home() / "AppData" / "Local") / "dev-status-widget"
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME")
        base_dir = Path(xdg_data) / "dev-status-widget" if xdg_data else Path.home() / ".local" / "share" / "dev-status-widget"
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def generate_and_save(
    jira_provider,
    github_provider,
    db: DatabaseManager,
    production_branch: str,
    is_automatic: bool = False,
    reports_dir: Optional[Path] = None,
) -> Optional[SprintFreezeReport]:
    """
    Gera um relatório completo: busca as tarefas atuais do Jira, descobre a
    sprint ativa, cruza com o GitHub, renderiza o PDF e salva o registro no
    banco. Retorna None se não houver tarefas de nível superior na sprint ou
    nenhuma sprint ativa for encontrada. Se a busca no Jira falhar de fato
    (credenciais inválidas, JQL inválida, rede fora), levanta RuntimeError
    com a mensagem retornada pelo provedor, para que a UI exiba o erro real
    em vez de "nenhuma sprint ativa".
    """
    jira_result = jira_provider.fetch()
    jira_errors = jira_result.get("errors", [])
    jira_tasks: List[JiraTaskItem] = jira_result.get("items", [])
    top_level_tasks = [t for t in jira_tasks if not t.is_subtask]
    if not top_level_tasks:
        if jira_errors:
            raise RuntimeError("; ".join(jira_errors))
        return None

    sprint_info = jira_provider.get_active_sprint(top_level_tasks[0].key)
    if sprint_info is None:
        return None

    task_keys = [t.key for t in top_level_tasks]
    promotion_status, github_search_failed = github_provider.search_promotion_prs(task_keys, production_branch)

    report = build_report(
        top_level_tasks, sprint_info, promotion_status,
        is_automatic=is_automatic, github_search_failed=github_search_failed
    )

    target_dir = reports_dir or default_reports_dir()
    safe_sprint_name = "".join(c if c.isalnum() else "_" for c in report.sprint_name).strip("_") or report.sprint_id
    filename = f"{safe_sprint_name}_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = str(target_dir / filename)
    render_report_pdf(report, pdf_path)
    report.pdf_path = pdf_path

    report.id = db.save_freeze_report(report)
    return report

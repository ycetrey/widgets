"""
Testes automatizados para o serviço de Relatório de Sprint Freeze.
"""
import unittest
from datetime import date, datetime, timedelta, timezone

from src.core.models import JiraSprintInfo, JiraTaskItem


def _make_task(key, status, status_category, is_subtask=False):
    now = datetime.now(timezone.utc)
    return JiraTaskItem(
        key=key,
        summary=f"Tarefa {key}",
        status=status,
        status_category=status_category,
        priority="Média",
        issue_type="Tarefa",
        assignee="Dev",
        created_at=now,
        updated_at=now,
        html_url=f"https://jira.com/{key}",
        is_subtask=is_subtask
    )


class TestBuildReport(unittest.TestCase):
    def setUp(self):
        from src.core.sprint_freeze import build_report
        self.build_report = build_report
        self.sprint_info = JiraSprintInfo(
            id=42, name="Sprint 42",
            start_date=datetime.now(timezone.utc) - timedelta(days=14),
            end_date=datetime.now(timezone.utc)
        )

    def test_merged_pr_counts_as_promoted(self):
        tasks = [_make_task("FF-1", "Concluído", "done")]
        promotion_status = {"FF-1": {"merged": True, "pr_url": "https://github.com/org/repo/pull/1"}}

        report = self.build_report(tasks, self.sprint_info, promotion_status)

        self.assertEqual(report.promoted_count, 1)
        self.assertEqual(report.retained_count, 0)
        self.assertEqual(report.retained_tasks, [])

    def test_open_pr_is_retained_with_pr_diagnosis(self):
        tasks = [_make_task("FF-2", "Em Progresso", "indeterminate")]
        promotion_status = {"FF-2": {"merged": False, "pr_url": "https://github.com/org/repo/pull/2"}}

        report = self.build_report(tasks, self.sprint_info, promotion_status)

        self.assertEqual(report.retained_count, 1)
        self.assertEqual(report.retained_tasks[0].diagnosis, "⚠️ PR aberta aguardando merge")
        self.assertEqual(report.retained_tasks[0].pr_url, "https://github.com/org/repo/pull/2")

    def test_no_pr_uses_jira_status_as_diagnosis(self):
        tasks = [_make_task("FF-3", "A Fazer", "new")]
        report = self.build_report(tasks, self.sprint_info, {})

        self.assertEqual(report.retained_count, 1)
        self.assertEqual(report.retained_tasks[0].diagnosis, "🔨 A Fazer")
        self.assertIsNone(report.retained_tasks[0].pr_url)

    def test_subtasks_are_excluded_from_report(self):
        tasks = [
            _make_task("FF-4", "A Fazer", "new"),
            _make_task("FF-4-SUB1", "A Fazer", "new", is_subtask=True)
        ]
        report = self.build_report(tasks, self.sprint_info, {})

        self.assertEqual(report.total_tasks, 1)

    def test_github_search_failure_marks_diagnosis_as_unverified(self):
        tasks = [_make_task("FF-5", "A Fazer", "new")]
        report = self.build_report(tasks, self.sprint_info, {}, github_search_failed=True)

        self.assertEqual(report.retained_tasks[0].diagnosis, "❔ Não foi possível verificar PR")


class TestShouldGenerateAutomaticReport(unittest.TestCase):
    MONDAY = date(2024, 1, 1)   # 2024-01-01 é uma segunda-feira
    TUESDAY = date(2024, 1, 2)

    def setUp(self):
        from src.core.sprint_freeze import should_generate_automatic_report
        self.should_generate = should_generate_automatic_report

    def test_generates_on_freeze_monday(self):
        sprint_end = datetime(2023, 12, 31, tzinfo=timezone.utc)
        self.assertTrue(self.should_generate(self.MONDAY, sprint_end, already_has_automatic=False))

    def test_skips_if_already_generated(self):
        sprint_end = datetime(2023, 12, 31, tzinfo=timezone.utc)
        self.assertFalse(self.should_generate(self.MONDAY, sprint_end, already_has_automatic=True))

    def test_skips_on_non_monday(self):
        sprint_end = datetime(2023, 12, 31, tzinfo=timezone.utc)
        self.assertFalse(self.should_generate(self.TUESDAY, sprint_end, already_has_automatic=False))

    def test_skips_if_sprint_not_ended_yet(self):
        sprint_end = datetime(2024, 1, 5, tzinfo=timezone.utc)
        self.assertFalse(self.should_generate(self.MONDAY, sprint_end, already_has_automatic=False))

    def test_skips_if_no_sprint_end_date(self):
        self.assertFalse(self.should_generate(self.MONDAY, None, already_has_automatic=False))

"""
Testes automatizados para o serviço de Relatório de Sprint Freeze.
"""
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

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


class TestGenerateAndSave(unittest.TestCase):
    def setUp(self):
        self.tmp_db = "tests_tmp_freeze_generate.db"
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)
        from src.core.database import DatabaseManager
        self.db = DatabaseManager(custom_path=self.tmp_db)

    def tearDown(self):
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)

    @patch("src.core.sprint_freeze.render_report_pdf")
    def test_generate_and_save_persists_report(self, mock_render_pdf):
        mock_render_pdf.side_effect = lambda report, path: path

        jira_provider = MagicMock()
        jira_provider.fetch.return_value = {
            "items": [_make_task("FF-9", "A Fazer", "new")],
            "new_items": [],
            "errors": []
        }
        jira_provider.get_active_sprint.return_value = JiraSprintInfo(
            id=99, name="Sprint 99", start_date=None, end_date=None
        )

        github_provider = MagicMock()
        github_provider.search_promotion_prs.return_value = ({}, False)

        from src.core.sprint_freeze import generate_and_save
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            report = generate_and_save(
                jira_provider, github_provider, self.db,
                production_branch="rc-prod",
                is_automatic=True,
                reports_dir=Path(tmp_dir)
            )

        self.assertIsNotNone(report)
        self.assertEqual(report.sprint_name, "Sprint 99")
        self.assertTrue(report.is_automatic)
        self.assertGreater(report.id, 0)

        stored = self.db.get_freeze_reports()
        self.assertEqual(len(stored), 1)
        self.assertTrue(self.db.has_automatic_freeze_report("99"))

    def test_generate_and_save_returns_none_without_active_sprint(self):
        jira_provider = MagicMock()
        jira_provider.fetch.return_value = {
            "items": [_make_task("FF-9", "A Fazer", "new")],
            "new_items": [],
            "errors": []
        }
        jira_provider.get_active_sprint.return_value = None
        github_provider = MagicMock()

        from src.core.sprint_freeze import generate_and_save
        report = generate_and_save(jira_provider, github_provider, self.db, production_branch="rc-prod")
        self.assertIsNone(report)

    def test_generate_and_save_returns_none_without_top_level_tasks(self):
        jira_provider = MagicMock()
        jira_provider.fetch.return_value = {
            "items": [_make_task("FF-9-SUB1", "A Fazer", "new", is_subtask=True)],
            "new_items": [],
            "errors": []
        }
        github_provider = MagicMock()

        from src.core.sprint_freeze import generate_and_save
        report = generate_and_save(jira_provider, github_provider, self.db, production_branch="rc-prod")
        self.assertIsNone(report)
        jira_provider.get_active_sprint.assert_not_called()


class TestFreezeReportCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_card_shows_summary_and_emits_download(self):
        from src.ui.widgets.freeze_report_card import FreezeReportCard
        from src.core.models import SprintFreezeReport

        report = SprintFreezeReport(
            id=1, sprint_id="10", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=True,
            total_tasks=18, promoted_count=11, retained_count=7,
            pdf_path="/tmp/relatorio.pdf"
        )
        card = FreezeReportCard(report)

        captured = []
        card.download_clicked.connect(lambda path: captured.append(path))
        card.download_btn.click()

        self.assertEqual(captured, ["/tmp/relatorio.pdf"])
        self.assertIn("11 promovidas", card.summary_label.text())
        self.assertIn("7 retidas", card.summary_label.text())


class TestFreezeReportView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_set_reports_renders_cards_and_status(self):
        from src.ui.views.freeze_report_view import FreezeReportView
        from src.core.models import SprintFreezeReport

        view = FreezeReportView()
        reports = [
            SprintFreezeReport(
                id=1, sprint_id="10", sprint_name="Sprint 42",
                generated_at=datetime.now(timezone.utc), is_automatic=False,
                total_tasks=18, promoted_count=11, retained_count=7,
                pdf_path="/tmp/r.pdf"
            )
        ]

        captured = []
        view.download_requested.connect(lambda path: captured.append(path))
        view.set_reports(reports)

        self.assertEqual(view.cards_layout.count(), 1)
        self.assertIn("11 promovidas", view.status_label.text())

        # Verify signal forwarding: click the card's download button
        card = view.cards_layout.itemAt(0).widget()
        card.download_btn.click()
        self.assertEqual(captured, ["/tmp/r.pdf"])

    def test_generate_button_emits_signal(self):
        from src.ui.views.freeze_report_view import FreezeReportView

        view = FreezeReportView()
        captured = []
        view.generate_requested.connect(lambda: captured.append(True))
        view.generate_btn.click()
        self.assertEqual(captured, [True])

    def test_set_generating_disables_button(self):
        from src.ui.views.freeze_report_view import FreezeReportView

        view = FreezeReportView()
        view.set_generating(True)
        self.assertFalse(view.generate_btn.isEnabled())
        view.set_generating(False)
        self.assertTrue(view.generate_btn.isEnabled())

    def test_set_reports_clears_previous_cards(self):
        from src.ui.views.freeze_report_view import FreezeReportView
        from src.core.models import SprintFreezeReport

        view = FreezeReportView()

        # First render with one report
        report_a = SprintFreezeReport(
            id=1, sprint_id="10", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=False,
            total_tasks=18, promoted_count=11, retained_count=7,
            pdf_path="/tmp/r1.pdf"
        )
        view.set_reports([report_a])
        self.assertEqual(view.cards_layout.count(), 1)

        # Second render with two reports
        report_b = SprintFreezeReport(
            id=2, sprint_id="11", sprint_name="Sprint 43",
            generated_at=datetime.now(timezone.utc), is_automatic=True,
            total_tasks=20, promoted_count=15, retained_count=5,
            pdf_path="/tmp/r2.pdf"
        )
        report_c = SprintFreezeReport(
            id=3, sprint_id="12", sprint_name="Sprint 44",
            generated_at=datetime.now(timezone.utc), is_automatic=False,
            total_tasks=16, promoted_count=10, retained_count=6,
            pdf_path="/tmp/r3.pdf"
        )
        view.set_reports([report_b, report_c])

        # Assert only 2 cards exist (not 1+2=3)
        self.assertEqual(view.cards_layout.count(), 2)

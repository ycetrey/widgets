"""
Testes automatizados para a camada de banco de dados SQLite e layout Kanban.
"""
import os
import unittest
from datetime import datetime, timezone

from src.core.database import DatabaseManager
from src.core.models import JiraTaskItem, PullRequestItem, SprintFreezeReport
from src.ui.widgets.kanban_swimlane import get_column_index


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.tmp_db = "tests_tmp_database.db"
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)
        self.db = DatabaseManager(custom_path=self.tmp_db)

    def tearDown(self):
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)

    def test_jira_tasks_roundtrip(self):
        now = datetime.now(timezone.utc)
        task = JiraTaskItem(
            key="FF-464",
            summary="Configurar registro operacional",
            status="CODE REVIEW",
            status_category="indeterminate",
            priority="Medium",
            issue_type="Tarefa Técnica",
            assignee="Antonio",
            created_at=now,
            updated_at=now,
            html_url="https://jira.com/FF-464",
            parent_key="FF-406",
            parent_summary="API Integra",
            parent_status="To Do"
        )
        self.db.save_jira_tasks([task])
        loaded = self.db.get_jira_tasks()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].key, "FF-464")
        self.assertEqual(loaded[0].summary, "Configurar registro operacional")
        self.assertEqual(loaded[0].parent_key, "FF-406")
        self.assertEqual(loaded[0].parent_summary, "API Integra")

    def test_pull_requests_roundtrip(self):
        now = datetime.now(timezone.utc)
        pr = PullRequestItem(
            id=101,
            number=42,
            title="Refactor auth",
            repo="org/api",
            author="junior",
            author_avatar="https://avatar.png",
            html_url="https://github.com/org/api/pull/42",
            created_at=now,
            labels=["bug", "urgent"],
            comments_count=3,
            review_decision="REVIEW_REQUIRED"
        )
        self.db.save_pull_requests([pr])
        loaded = self.db.get_pull_requests()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, 101)
        self.assertEqual(loaded[0].number, 42)
        self.assertEqual(loaded[0].labels, ["bug", "urgent"])
        self.assertEqual(loaded[0].comments_count, 3)
        self.assertEqual(loaded[0].review_decision, "REVIEW_REQUIRED")
        self.assertEqual(loaded[0].status_key, "review_required")

    def test_notification_deduplication(self):
        now = datetime.now(timezone.utc)
        task1 = JiraTaskItem(
            key="FF-1", summary="T1", status="To Do", status_category="new",
            priority="Medium", issue_type="Bug", assignee="Eu",
            created_at=now, updated_at=now, html_url="url1"
        )
        task2 = JiraTaskItem(
            key="FF-2", summary="T2", status="In Progress", status_category="indeterminate",
            priority="High", issue_type="Task", assignee="Eu",
            created_at=now, updated_at=now, html_url="url2"
        )

        # 1ª execução com banco vazio: não gera notificação em lote
        new_first = self.db.detect_and_record_new_jira([task1, task2])
        self.assertEqual(len(new_first), 0)

        # 2ª execução com mesma lista: zero novos
        new_second = self.db.detect_and_record_new_jira([task1, task2])
        self.assertEqual(len(new_second), 0)

        # 3ª execução com nova tarefa: detecta somente a nova
        task3 = JiraTaskItem(
            key="FF-3", summary="T3", status="To Do", status_category="new",
            priority="Low", issue_type="Task", assignee="Eu",
            created_at=now, updated_at=now, html_url="url3"
        )
        new_third = self.db.detect_and_record_new_jira([task1, task2, task3])
        self.assertEqual(len(new_third), 1)
        self.assertEqual(new_third[0].key, "FF-3")


class TestKanbanMapping(unittest.TestCase):
    def test_status_mapping(self):
        # A FAZER = 0
        self.assertEqual(get_column_index("To Do", "new"), 0)
        self.assertEqual(get_column_index("A Fazer", "new"), 0)

        # EM ANDAMENTO = 1
        self.assertEqual(get_column_index("In Progress", "indeterminate"), 1)
        self.assertEqual(get_column_index("Em Andamento", "indeterminate"), 1)

        # CODE REVIEW = 2
        self.assertEqual(get_column_index("CODE REVIEW", "indeterminate"), 2)
        self.assertEqual(get_column_index("Em Code Review", "indeterminate"), 2)

        # EM HOMOLOGAÇÃO (QA) = 3
        self.assertEqual(get_column_index("Em Homologação (QA)", "indeterminate"), 3)
        self.assertEqual(get_column_index("QA", "indeterminate"), 3)

        # CONCLUÍDO = 4
        self.assertEqual(get_column_index("Done", "done"), 4)
        self.assertEqual(get_column_index("Concluído", "done"), 4)


class TestFreezeReportsDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp_db = "tests_tmp_freeze_reports.db"
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)
        self.db = DatabaseManager(custom_path=self.tmp_db)

    def tearDown(self):
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)

    def test_save_and_get_freeze_reports(self):
        report = SprintFreezeReport(
            id=0, sprint_id="42", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=True,
            total_tasks=18, promoted_count=11, retained_count=7, pdf_path="/tmp/r.pdf"
        )

        report_id = self.db.save_freeze_report(report)
        self.assertGreater(report_id, 0)

        stored = self.db.get_freeze_reports()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].sprint_name, "Sprint 42")
        self.assertEqual(stored[0].promoted_count, 11)
        self.assertTrue(stored[0].is_automatic)

    def test_has_automatic_freeze_report(self):
        self.assertFalse(self.db.has_automatic_freeze_report("42"))

        manual = SprintFreezeReport(
            id=0, sprint_id="42", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=False,
            total_tasks=1, promoted_count=1, retained_count=0, pdf_path="/tmp/a.pdf"
        )
        self.db.save_freeze_report(manual)
        self.assertFalse(self.db.has_automatic_freeze_report("42"))

        automatic = SprintFreezeReport(
            id=0, sprint_id="42", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=True,
            total_tasks=1, promoted_count=0, retained_count=1, pdf_path="/tmp/b.pdf"
        )
        self.db.save_freeze_report(automatic)
        self.assertTrue(self.db.has_automatic_freeze_report("42"))

    def test_delete_freeze_report(self):
        report = SprintFreezeReport(
            id=0, sprint_id="42", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=False,
            total_tasks=5, promoted_count=3, retained_count=2, pdf_path="/tmp/test_del.pdf"
        )
        report_id = self.db.save_freeze_report(report)
        self.assertEqual(len(self.db.get_freeze_reports()), 1)

        pdf_path = self.db.delete_freeze_report(report_id)
        self.assertEqual(pdf_path, "/tmp/test_del.pdf")
        self.assertEqual(len(self.db.get_freeze_reports()), 0)

    def test_delete_all_freeze_reports(self):
        r1 = SprintFreezeReport(
            id=0, sprint_id="42", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=False,
            total_tasks=5, promoted_count=3, retained_count=2, pdf_path="/tmp/r1.pdf"
        )
        r2 = SprintFreezeReport(
            id=0, sprint_id="43", sprint_name="Sprint 43",
            generated_at=datetime.now(timezone.utc), is_automatic=True,
            total_tasks=8, promoted_count=6, retained_count=2, pdf_path="/tmp/r2.pdf"
        )
        self.db.save_freeze_report(r1)
        self.db.save_freeze_report(r2)
        self.assertEqual(len(self.db.get_freeze_reports()), 2)

        paths = self.db.delete_all_freeze_reports()
        self.assertEqual(set(paths), {"/tmp/r1.pdf", "/tmp/r2.pdf"})
        self.assertEqual(len(self.db.get_freeze_reports()), 0)

    def test_database_path_resolution_windows(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("sys.platform", "win32"), \
                 patch.dict(os.environ, {"LOCALAPPDATA": tmp_dir}):
                resolved = self.db._resolve_db_path(None)
                expected = os.path.join(tmp_dir, "dev-status-widget", "widget.db")
                self.assertEqual(str(resolved), expected)

    def test_database_path_resolution_linux_xdg(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("sys.platform", "linux"), \
                 patch.dict(os.environ, {"XDG_DATA_HOME": tmp_dir}):
                resolved = self.db._resolve_db_path(None)
                expected = os.path.join(tmp_dir, "dev-status-widget", "widget.db")
                self.assertEqual(str(resolved), expected)


if __name__ == "__main__":
    unittest.main()


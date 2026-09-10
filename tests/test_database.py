"""
Testes automatizados para a camada de banco de dados SQLite e layout Kanban.
"""
import os
import unittest
from datetime import datetime, timezone

from src.core.database import DatabaseManager
from src.core.models import JiraTaskItem, PullRequestItem
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
            comments_count=3
        )
        self.db.save_pull_requests([pr])
        loaded = self.db.get_pull_requests()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, 101)
        self.assertEqual(loaded[0].number, 42)
        self.assertEqual(loaded[0].labels, ["bug", "urgent"])
        self.assertEqual(loaded[0].comments_count, 3)

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


if __name__ == "__main__":
    unittest.main()


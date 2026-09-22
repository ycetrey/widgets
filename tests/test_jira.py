"""
Testes automatizados para a integração com o Jira.
"""
import os
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.core.models import AppConfig, JiraSprintInfo, JiraTaskItem
from src.core.config import ConfigManager
from src.providers.jira_provider import JiraProvider


class TestJiraModels(unittest.TestCase):
    def test_updated_humanized(self):
        now = datetime.now(timezone.utc)

        task1 = JiraTaskItem(
            key="DEV-101",
            summary="Refatoração de API",
            status="Em Progresso",
            status_category="indeterminate",
            priority="Alta",
            issue_type="História",
            assignee="Você",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(minutes=25),
            html_url="https://jira.com/DEV-101"
        )
        self.assertIn("min", task1.updated_humanized)

        task2 = JiraTaskItem(
            key="DEV-102",
            summary="Bug no login",
            status="A Fazer",
            status_category="new",
            priority="Crítica",
            issue_type="Bug",
            assignee="Você",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(hours=4),
            html_url="https://jira.com/DEV-102"
        )
        self.assertIn("h", task2.updated_humanized)


class TestJiraProvider(unittest.TestCase):
    def test_mock_data(self):
        provider = JiraProvider(demo_mode=True)
        # 1º ciclo
        res1 = provider.fetch()
        self.assertGreater(len(res1["items"]), 0)
        self.assertEqual(len(res1["new_items"]), 0)

        # 2º ciclo: detecta nova tarefa
        res2 = provider.fetch()
        self.assertGreater(len(res2["new_items"]), 0)

    @patch("requests.get")
    def test_api_fetch(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "issues": [
                {
                    "key": "PROJ-10",
                    "fields": {
                        "summary": "Implementar tela de login",
                        "status": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}},
                        "priority": {"name": "High"},
                        "issuetype": {"name": "Story"},
                        "assignee": {"displayName": "Dev User"},
                        "created": "2024-03-01T10:00:00Z",
                        "updated": "2024-03-02T15:30:00Z"
                    }
                }
            ]
        }
        mock_get.return_value = mock_resp

        provider = JiraProvider(
            jira_url="https://minhaempresa.atlassian.net",
            email="dev@empresa.com",
            api_token="dummy_token",
            demo_mode=False
        )

        result = provider.fetch()
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(item.key, "PROJ-10")
        self.assertEqual(item.status, "In Progress")
        self.assertEqual(item.priority, "High")
        self.assertEqual(item.html_url, "https://minhaempresa.atlassian.net/browse/PROJ-10")

        # Verifica que o endpoint chamado foi /rest/api/3/search/jql
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "https://minhaempresa.atlassian.net/rest/api/3/search/jql")

    @patch("requests.get")
    def test_api_fetch_fallback(self, mock_get):
        resp_404 = MagicMock()
        resp_404.status_code = 404

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "issues": [
                {
                    "key": "SRV-20",
                    "fields": {
                        "summary": "Jira Server issue",
                        "status": {"name": "Open"},
                        "priority": {"name": "Low"},
                        "issuetype": {"name": "Task"},
                        "assignee": {"displayName": "Admin"},
                        "created": "2024-03-01T10:00:00Z",
                        "updated": "2024-03-02T15:30:00Z"
                    }
                }
            ]
        }

        # Simula: primeiro endpoint (/jql) dá 404, fallback (/search v3) dá 200
        mock_get.side_effect = [resp_404, resp_200]

        provider = JiraProvider(
            jira_url="https://jira-local.empresa.com",
            email="dev@empresa.com",
            api_token="token",
            demo_mode=False
        )

        result = provider.fetch()
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0].key, "SRV-20")
        self.assertEqual(mock_get.call_count, 2)


class TestJiraConfigPersistence(unittest.TestCase):
    def test_save_and_load_jira_settings(self):
        tmp = "tests_tmp_jira_config.yaml"
        if os.path.exists(tmp):
            os.remove(tmp)

        try:
            cm = ConfigManager(custom_path=tmp)
            self.assertFalse(cm.config.jira_enabled)

            cm.config.jira_enabled = True
            cm.config.jira_url = "https://teste.atlassian.net"
            cm.config.jira_email = "eu@teste.com"
            cm.config.jira_api_token = "tok123"
            cm.save()

            cm2 = ConfigManager(custom_path=tmp)
            self.assertTrue(cm2.config.jira_enabled)
            self.assertEqual(cm2.config.jira_url, "https://teste.atlassian.net")
            self.assertEqual(cm2.config.jira_email, "eu@teste.com")
            self.assertEqual(cm2.config.jira_api_token, "tok123")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


class TestJiraHierarchyParsing(unittest.TestCase):
    @patch("requests.get")
    def test_epic_vs_story_and_subtasks(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "issues": [
                {
                    "key": "FF-617",
                    "fields": {
                        "summary": "Aceitar CNPJ alfanumérico",
                        "status": {"name": "CODE REVIEW", "statusCategory": {"key": "indeterminate"}},
                        "priority": {"name": "Medium"},
                        "issuetype": {"name": "Story", "subtask": False, "hierarchyLevel": 0},
                        "assignee": {"displayName": "Ricardo Silva"},
                        "created": "2024-03-01T10:00:00Z",
                        "updated": "2024-03-02T15:30:00Z",
                        "parent": {
                            "key": "FF-403",
                            "fields": {
                                "summary": "API Integra — Acesso e cobrança",
                                "issuetype": {"name": "Epic", "subtask": False, "hierarchyLevel": 1}
                            }
                        },
                        "subtasks": [
                            {
                                "key": "FF-618",
                                "fields": {
                                    "summary": "Dev: Desenvolvimento",
                                    "status": {"name": "Done", "statusCategory": {"key": "done"}},
                                    "priority": {"name": "Medium"},
                                    "issuetype": {"name": "Subtarefa de Desenvolvimento", "subtask": True, "hierarchyLevel": -1}
                                }
                            },
                            {
                                "key": "FF-679",
                                "fields": {
                                    "summary": "Dev: Integração",
                                    "status": {"name": "To Do", "statusCategory": {"key": "new"}},
                                    "priority": {"name": "Medium"},
                                    "issuetype": {"name": "Subtarefa de Integração", "subtask": True, "hierarchyLevel": -1}
                                }
                            }
                        ]
                    }
                },
                {
                    "key": "FF-661",
                    "fields": {
                        "summary": "CR: Code Review",
                        "status": {"name": "Done", "statusCategory": {"key": "done"}},
                        "priority": {"name": "Medium"},
                        "issuetype": {"name": "Subtarefa de Code Review", "subtask": True, "hierarchyLevel": -1},
                        "assignee": {"displayName": "Antonio Junior"},
                        "created": "2024-03-01T10:00:00Z",
                        "updated": "2024-03-02T15:30:00Z",
                        "parent": {
                            "key": "FF-617",
                            "fields": {
                                "summary": "Aceitar CNPJ alfanumérico",
                                "status": {"name": "CODE REVIEW"},
                                "issuetype": {"name": "Story", "subtask": False, "hierarchyLevel": 0}
                            }
                        }
                    }
                }
            ]
        }
        mock_resp_batch = MagicMock()
        mock_resp_batch.status_code = 200
        mock_resp_batch.json.return_value = {
            "issues": [
                {
                    "key": "FF-618",
                    "fields": {
                        "summary": "Dev: Desenvolvimento",
                        "status": {"name": "Done", "statusCategory": {"key": "done"}},
                        "priority": {"name": "Medium"},
                        "issuetype": {"name": "Subtarefa de Desenvolvimento", "subtask": True, "hierarchyLevel": -1},
                        "assignee": {"displayName": "Ricardo Silva"},
                        "created": "2024-03-01T10:00:00Z",
                        "updated": "2024-03-02T15:30:00Z",
                        "parent": {"key": "FF-617", "fields": {"summary": "Aceitar CNPJ alfanumérico", "issuetype": {"name": "Story"}}}
                    }
                },
                {
                    "key": "FF-679",
                    "fields": {
                        "summary": "QA: Validação",
                        "status": {"name": "To Do", "statusCategory": {"key": "new"}},
                        "priority": {"name": "Medium"},
                        "issuetype": {"name": "Subtarefa de QA", "subtask": True, "hierarchyLevel": -1},
                        "assignee": {"displayName": "Nicolle Emanuele"},
                        "created": "2024-03-01T10:00:00Z",
                        "updated": "2024-03-02T15:30:00Z",
                        "parent": {"key": "FF-617", "fields": {"summary": "Aceitar CNPJ alfanumérico", "issuetype": {"name": "Story"}}}
                    }
                }
            ]
        }
        mock_get.side_effect = [mock_resp, mock_resp_batch]

        provider = JiraProvider(
            jira_url="https://fiscalmax.atlassian.net",
            email="dev@empresa.com",
            api_token="token",
            demo_mode=False
        )

        result = provider.fetch()
        items = result["items"]
        self.assertEqual(len(items), 4)

        # 1. Valida História FF-617
        story = next(i for i in items if i.key == "FF-617")
        self.assertFalse(story.is_subtask)
        self.assertEqual(story.epic_key, "FF-403")
        self.assertEqual(story.epic_summary, "API Integra — Acesso e cobrança")
        self.assertIsNone(story.parent_key)  # Não pode ter parent_key apontando para o épico!
        self.assertEqual(len(story.subtasks_list), 2)
        self.assertEqual(story.subtasks_list[0]["key"], "FF-618")
        self.assertEqual(story.subtasks_list[1]["key"], "FF-679")

        # 2. Valida Subtarefa FF-661
        subtask = next(i for i in items if i.key == "FF-661")
        self.assertTrue(subtask.is_subtask)
        self.assertEqual(subtask.parent_key, "FF-617")
        self.assertEqual(subtask.parent_summary, "Aceitar CNPJ alfanumérico")
        self.assertEqual(subtask.parent_issue_type, "Story")

        # 3. Valida Subtarefa de QA FF-679 com assignee real (Nicolle Emanuele)
        qa_subtask = next(i for i in items if i.key == "FF-679")
        self.assertTrue(qa_subtask.is_subtask)
        self.assertEqual(qa_subtask.assignee, "Nicolle Emanuele")
        self.assertEqual(qa_subtask.parent_key, "FF-617")


class TestJiraFilteringAndTratativas(unittest.TestCase):
    def test_default_jql_filters_subtasks(self):
        self.assertIn("issuetype not in subtaskIssueTypes()", JiraProvider.DEFAULT_JQL)

    def test_legacy_default_jql_migration(self):
        import yaml
        tmp = "tests_tmp_legacy_jql.yaml"
        if os.path.exists(tmp):
            os.remove(tmp)

        try:
            with open(tmp, "w", encoding="utf-8") as f:
                yaml.safe_dump({
                    "jira_jql": "sprint in openSprints() AND (assignee = currentUser() OR assignee is EMPTY) ORDER BY updated DESC"
                }, f)

            cm = ConfigManager(custom_path=tmp)
            self.assertEqual(cm.config.jira_jql, ConfigManager.DEFAULT_JIRA_JQL)
            self.assertIn("issuetype not in subtaskIssueTypes()", cm.config.jira_jql)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_user_filtering_excludes_external_story_subtasks(self):
        from PyQt6.QtWidgets import QApplication
        from src.ui.views.jira_view import JiraView
        app = QApplication.instance() or QApplication(["-platform", "offscreen"])

        now = datetime.now(timezone.utc)
        # História do próprio usuário
        my_story = JiraTaskItem(
            key="FF-474",
            summary="Minha história na sprint",
            status="Em Desenvolvimento",
            status_category="indeterminate",
            priority="Alta",
            issue_type="Story",
            assignee="Antonio Barbosa Junior",
            created_at=now,
            updated_at=now,
            html_url="https://jira/FF-474",
            is_subtask=False
        )
        # Subtarefa da história do próprio usuário
        my_subtask = JiraTaskItem(
            key="FF-649",
            summary="Desenvolvimento da minha história",
            status="Em Andamento",
            status_category="indeterminate",
            priority="Alta",
            issue_type="Subtarefa de Desenvolvimento",
            assignee="Antonio Barbosa Junior",
            created_at=now,
            updated_at=now,
            html_url="https://jira/FF-649",
            is_subtask=True,
            parent_key="FF-474",
            parent_summary="Minha história na sprint"
        )
        # Subtarefa de Code Review feita em história de outro dev (Ricardo - FF-617)
        external_cr_subtask = JiraTaskItem(
            key="FF-661",
            summary="CR: Code Review",
            status="Done",
            status_category="done",
            priority="Média",
            issue_type="Subtarefa de Code Review",
            assignee="Antonio Barbosa Junior",
            created_at=now,
            updated_at=now,
            html_url="https://jira/FF-661",
            is_subtask=True,
            parent_key="FF-617",
            parent_summary="Aceitar CNPJ alfanumérico na validação de identificadores"
        )

        jira_view = JiraView()
        tasks = [my_story, my_subtask, external_cr_subtask]
        jira_view.update_tasks(tasks, current_user_name="Antonio Barbosa Junior")

        # Verifica se na renderização do Kanban a história externa FF-617 NÃO gerou swimlane
        # Deve existir exatamente 1 swimlane (FF-474) e nenhuma para FF-617
        swimlanes = [
            jira_view.cards_layout.itemAt(i).widget()
            for i in range(jira_view.cards_layout.count())
            if jira_view.cards_layout.itemAt(i).widget()
        ]
        swimlane_keys = [getattr(s, "parent_key", "") for s in swimlanes if hasattr(s, "parent_key")]
        self.assertIn("FF-474", swimlane_keys)
        self.assertNotIn("FF-617", swimlane_keys)


class TestJiraActiveSprint(unittest.TestCase):
    @patch("requests.get")
    def test_get_active_sprint_success(self, mock_get):
        board_resp = MagicMock()
        board_resp.status_code = 200
        board_resp.json.return_value = {"values": [{"id": 7, "name": "Board FF"}]}

        sprint_resp = MagicMock()
        sprint_resp.status_code = 200
        sprint_resp.json.return_value = {
            "values": [{
                "id": 42,
                "name": "Sprint 42",
                "startDate": "2026-09-08T13:00:00.000Z",
                "endDate": "2026-09-22T13:00:00.000Z"
            }]
        }
        mock_get.side_effect = [board_resp, sprint_resp]

        provider = JiraProvider(
            jira_url="https://empresa.atlassian.net",
            email="dev@empresa.com",
            api_token="token123"
        )
        sprint = provider.get_active_sprint("FF-1234")

        self.assertIsNotNone(sprint)
        self.assertEqual(sprint.id, 42)
        self.assertEqual(sprint.name, "Sprint 42")
        self.assertEqual(sprint.end_date.day, 22)

    @patch("requests.get")
    def test_get_active_sprint_no_active_sprint_returns_none(self, mock_get):
        board_resp = MagicMock()
        board_resp.status_code = 200
        board_resp.json.return_value = {"values": [{"id": 7, "name": "Board FF"}]}

        sprint_resp = MagicMock()
        sprint_resp.status_code = 200
        sprint_resp.json.return_value = {"values": []}
        mock_get.side_effect = [board_resp, sprint_resp]

        provider = JiraProvider(
            jira_url="https://empresa.atlassian.net",
            email="dev@empresa.com",
            api_token="token123"
        )
        sprint = provider.get_active_sprint("FF-1234")
        self.assertIsNone(sprint)

    def test_get_active_sprint_demo_mode_returns_none(self):
        provider = JiraProvider(demo_mode=True)
        self.assertIsNone(provider.get_active_sprint("FF-1234"))


if __name__ == "__main__":
    unittest.main()

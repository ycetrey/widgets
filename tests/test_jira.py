"""
Testes automatizados para a integração com o Jira.
"""
import os
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.core.models import JiraTaskItem, AppConfig
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


if __name__ == "__main__":
    unittest.main()

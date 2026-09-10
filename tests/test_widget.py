"""
Testes automatizados para o Dev Status Widget.
"""
import os
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.core.models import PullRequestItem, AppConfig
from src.core.config import ConfigManager
from src.providers.github_provider import GitHubProvider


class TestCoreModels(unittest.TestCase):
    def test_age_and_urgency(self):
        now = datetime.now(timezone.utc)

        # PR com 20 dias (crítico)
        pr_old = PullRequestItem(
            id=1, number=101, title="Old PR", repo="org/repo",
            author="dev1", author_avatar="", html_url="https://github.com/org/repo/pull/101",
            created_at=now - timedelta(days=20)
        )
        self.assertEqual(pr_old.urgency_level, "critical")
        self.assertIn("dias", pr_old.age_humanized)

        # PR com 5 dias (warning)
        pr_mid = PullRequestItem(
            id=2, number=102, title="Mid PR", repo="org/repo",
            author="dev2", author_avatar="", html_url="https://github.com/org/repo/pull/102",
            created_at=now - timedelta(days=5)
        )
        self.assertEqual(pr_mid.urgency_level, "warning")

        # PR recente com 30 minutos (fresh)
        pr_fresh = PullRequestItem(
            id=3, number=103, title="Fresh PR", repo="org/repo",
            author="dev3", author_avatar="", html_url="https://github.com/org/repo/pull/103",
            created_at=now - timedelta(minutes=30)
        )
        self.assertEqual(pr_fresh.urgency_level, "fresh")
        self.assertIn("min", pr_fresh.age_humanized)

    def test_sorting_oldest_first(self):
        now = datetime.now(timezone.utc)
        pr1 = PullRequestItem(id=1, number=1, title="Mais Antiga", repo="r", author="a", author_avatar="", html_url="u1", created_at=now - timedelta(days=10))
        pr2 = PullRequestItem(id=2, number=2, title="Intermediária", repo="r", author="b", author_avatar="", html_url="u2", created_at=now - timedelta(days=5))
        pr3 = PullRequestItem(id=3, number=3, title="Mais Recente", repo="r", author="c", author_avatar="", html_url="u3", created_at=now - timedelta(hours=1))

        # Lista desordenada
        prs = [pr2, pr3, pr1]

        # Ordenação da mais antiga para a mais recente (created_at ASC)
        prs.sort(key=lambda p: p.created_at, reverse=False)

        self.assertEqual(prs[0].title, "Mais Antiga")
        self.assertEqual(prs[1].title, "Intermediária")
        self.assertEqual(prs[2].title, "Mais Recente")


class TestConfigManager(unittest.TestCase):
    def test_load_and_save(self):
        tmp_config_path = "tests_tmp_config.yaml"
        if os.path.exists(tmp_config_path):
            os.remove(tmp_config_path)

        try:
            cm = ConfigManager(custom_path=tmp_config_path)
            # Default
            self.assertEqual(cm.config.sort_order, "oldest_first")

            # Modifica e salva
            cm.config.github_token = "test_token_123"
            cm.config.repositories = ["myorg/myrepo"]
            cm.config.refresh_interval_minutes = 10
            saved = cm.save()
            self.assertTrue(saved)

            # Recarrega em nova instância
            cm2 = ConfigManager(custom_path=tmp_config_path)
            self.assertEqual(cm2.config.github_token, "test_token_123")
            self.assertEqual(cm2.config.repositories, ["myorg/myrepo"])
            self.assertEqual(cm2.config.refresh_interval_minutes, 10)
        finally:
            if os.path.exists(tmp_config_path):
                os.remove(tmp_config_path)


class TestGitHubProvider(unittest.TestCase):
    @patch("requests.get")
    def test_fetch_and_new_item_detection(self, mock_get):
        # Mock do retorno da API do GitHub
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 1001,
                "number": 42,
                "title": "Fix memory leak",
                "user": {"login": "octocat", "avatar_url": ""},
                "html_url": "https://github.com/test/repo/pull/42",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-02T10:00:00Z",
                "draft": False,
                "labels": [{"name": "bug"}],
                "comments": 2
            },
            {
                "id": 1002,
                "number": 43,
                "title": "Add feature",
                "user": {"login": "mona", "avatar_url": ""},
                "html_url": "https://github.com/test/repo/pull/43",
                "created_at": "2024-02-01T10:00:00Z",
                "updated_at": "2024-02-02T10:00:00Z",
                "draft": False,
                "labels": [],
                "comments": 0
            }
        ]
        mock_get.return_value = mock_response

        provider = GitHubProvider(repositories=["test/repo"], sort_order="oldest_first")

        # 1º Ciclo (Primeira execução)
        result1 = provider.fetch()
        self.assertEqual(len(result1["items"]), 2)
        # Primeiro item deve ser a PR mais antiga (#42 criada em janeiro)
        self.assertEqual(result1["items"][0].number, 42)
        # Na primeira execução, new_items deve ser vazio para evitar spam
        self.assertEqual(len(result1["new_items"]), 0)

        # 2º Ciclo (Chega uma nova PR #44)
        mock_response.json.return_value.append({
            "id": 1003,
            "number": 44,
            "title": "Brand new PR",
            "user": {"login": "alice", "avatar_url": ""},
            "html_url": "https://github.com/test/repo/pull/44",
            "created_at": "2024-03-01T10:00:00Z",
            "draft": False,
            "labels": [],
            "comments": 0
        })

        result2 = provider.fetch()
        self.assertEqual(len(result2["items"]), 3)
        # Detectou a nova PR
        self.assertEqual(len(result2["new_items"]), 1)
        self.assertEqual(result2["new_items"][0].number, 44)


if __name__ == "__main__":
    unittest.main()

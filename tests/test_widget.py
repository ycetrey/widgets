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

    def test_pr_status_resolution(self):
        now = datetime.now(timezone.utc)

        # 1. Aguardando Revisão explícito
        pr_review = PullRequestItem(
            id=1, number=10, title="PR 10", repo="org/repo", author="dev", author_avatar="",
            html_url="url", created_at=now, review_decision="REVIEW_REQUIRED"
        )
        self.assertEqual(pr_review.status_key, "review_required")
        self.assertEqual(pr_review.status_label, "Aguardando Revisão")
        self.assertIn("Aguardando Revisão", pr_review.status_display)

        # 2. Aprovada
        pr_approved = PullRequestItem(
            id=2, number=11, title="PR 11", repo="org/repo", author="dev", author_avatar="",
            html_url="url", created_at=now, review_decision="APPROVED"
        )
        self.assertEqual(pr_approved.status_key, "approved")
        self.assertEqual(pr_approved.status_label, "Aprovada")

        # 3. Mudanças Solicitadas
        pr_changes = PullRequestItem(
            id=3, number=12, title="PR 12", repo="org/repo", author="dev", author_avatar="",
            html_url="url", created_at=now, review_decision="CHANGES_REQUESTED"
        )
        self.assertEqual(pr_changes.status_key, "changes_requested")
        self.assertEqual(pr_changes.status_label, "Mudanças Solicitadas")

        # 4. Rascunho / Draft
        pr_draft = PullRequestItem(
            id=4, number=13, title="PR 13", repo="org/repo", author="dev", author_avatar="",
            html_url="url", created_at=now, is_draft=True, review_decision="REVIEW_REQUIRED"
        )
        self.assertEqual(pr_draft.status_key, "draft")
        self.assertEqual(pr_draft.status_label, "Rascunho")

        # 5. Heurística de label
        pr_label = PullRequestItem(
            id=5, number=14, title="PR 14", repo="org/repo", author="dev", author_avatar="",
            html_url="url", created_at=now, labels=["precisa-revisao"]
        )
        self.assertEqual(pr_label.status_key, "review_required")

        # 6. Aberta normal sem revisão
        pr_open = PullRequestItem(
            id=6, number=15, title="PR 15", repo="org/repo", author="dev", author_avatar="",
            html_url="url", created_at=now
        )
        self.assertEqual(pr_open.status_key, "open")
        self.assertEqual(pr_open.status_label, "Aberta")

    def test_sprint_freeze_dataclasses_defaults(self):
        from src.core.models import SprintFreezeTaskEntry, SprintFreezeReport, JiraSprintInfo

        entry = SprintFreezeTaskEntry(
            key="FF-1", summary="Tarefa", assignee="Dev", jira_status="A Fazer",
            html_url="https://jira.com/FF-1", diagnosis="🔨 A Fazer"
        )
        self.assertIsNone(entry.pr_url)

        report = SprintFreezeReport(
            id=0, sprint_id="10", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=False,
            total_tasks=1, promoted_count=0, retained_count=1, pdf_path=""
        )
        self.assertEqual(report.retained_tasks, [])

        sprint = JiraSprintInfo(id=10, name="Sprint 42", start_date=None, end_date=None)
        self.assertEqual(sprint.name, "Sprint 42")


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

    def test_freeze_report_config_roundtrip(self):
        tmp_config_path = "tests_tmp_config_freeze.yaml"
        if os.path.exists(tmp_config_path):
            os.remove(tmp_config_path)
        try:
            cm = ConfigManager(custom_path=tmp_config_path)
            self.assertFalse(cm.config.freeze_reports_enabled)
            self.assertEqual(cm.config.freeze_production_branch, "rc-prod")

            cm.config.freeze_reports_enabled = True
            cm.config.freeze_production_branch = "main"
            cm.save()

            cm2 = ConfigManager(custom_path=tmp_config_path)
            self.assertTrue(cm2.config.freeze_reports_enabled)
            self.assertEqual(cm2.config.freeze_production_branch, "main")
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


class TestGitHubProviderPromotionSearch(unittest.TestCase):
    @patch("requests.get")
    def test_search_promotion_prs_classifies_merged_and_open(self, mock_get):
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.json.return_value = {
            "items": [
                {
                    "title": "promote(FF-100): rc-prod",
                    "html_url": "https://github.com/org/repo/pull/10",
                    "pull_request": {"merged_at": "2026-09-20T10:00:00Z"}
                },
                {
                    "title": "promote(FF-200): rc-prod",
                    "html_url": "https://github.com/org/repo/pull/11",
                    "pull_request": {"merged_at": None}
                }
            ]
        }
        mock_get.return_value = search_resp

        provider = GitHubProvider(repositories=["org/repo"])
        result, had_error = provider.search_promotion_prs(["FF-100", "FF-200", "FF-300"], "rc-prod")

        self.assertFalse(had_error)
        self.assertTrue(result["FF-100"]["merged"])
        self.assertEqual(result["FF-100"]["pr_url"], "https://github.com/org/repo/pull/10")
        self.assertFalse(result["FF-200"]["merged"])
        self.assertNotIn("FF-300", result)

    @patch("requests.get")
    def test_search_promotion_prs_no_repositories_returns_empty(self, mock_get):
        provider = GitHubProvider(repositories=[])
        result, had_error = provider.search_promotion_prs(["FF-100"], "rc-prod")
        self.assertEqual(result, {})
        self.assertFalse(had_error)
        mock_get.assert_not_called()

    @patch("requests.get")
    def test_search_promotion_prs_marks_error_on_rate_limit(self, mock_get):
        error_resp = MagicMock()
        error_resp.status_code = 403
        mock_get.return_value = error_resp

        provider = GitHubProvider(repositories=["org/repo"])
        result, had_error = provider.search_promotion_prs(["FF-100"], "rc-prod")

        self.assertEqual(result, {})
        self.assertTrue(had_error)


class TestPullRequestsView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_status_filter_interaction(self):
        from src.ui.views.prs_view import PullRequestsView
        now = datetime.now(timezone.utc)
        view = PullRequestsView()

        pr_review = PullRequestItem(
            id=1, number=101, title="Refatorar API", repo="repo/a",
            author="carlos", author_avatar="", html_url="url1",
            created_at=now, review_decision="REVIEW_REQUIRED"
        )
        pr_approved = PullRequestItem(
            id=2, number=102, title="Corrigir bug", repo="repo/b",
            author="ana", author_avatar="", html_url="url2",
            created_at=now, review_decision="APPROVED"
        )
        pr_draft = PullRequestItem(
            id=3, number=103, title="Draft feature", repo="repo/a",
            author="marcos", author_avatar="", html_url="url3",
            created_at=now, is_draft=True
        )

        view.update_prs([pr_review, pr_approved, pr_draft])

        # Verifica opções populadas no combo
        self.assertEqual(view.status_combo.findData("all"), 0)
        self.assertNotEqual(view.status_combo.findData("review_required"), -1)
        self.assertNotEqual(view.status_combo.findData("approved"), -1)
        self.assertNotEqual(view.status_combo.findData("draft"), -1)

        # Sem filtro de status (all): 3 cards
        self.assertEqual(view.cards_layout.count(), 3)

        # Filtra por 'review_required' (Aguardando Revisão)
        idx_review = view.status_combo.findData("review_required")
        view.status_combo.setCurrentIndex(idx_review)
        self.assertEqual(view.cards_layout.count(), 1)

        # Filtra por 'approved'
        idx_appr = view.status_combo.findData("approved")
        view.status_combo.setCurrentIndex(idx_appr)
        self.assertEqual(view.cards_layout.count(), 1)

        # Filtra por 'changes_requested' (zero itens)
        idx_changes = view.status_combo.findData("changes_requested")
        view.status_combo.setCurrentIndex(idx_changes)
        self.assertEqual(view.cards_layout.count(), 1)
        lbl = view.cards_layout.itemAt(0).widget()
        self.assertIn("Nenhuma PR encontrada", lbl.text())

    def test_own_pr_identification(self):
        from src.ui.views.prs_view import PullRequestsView
        now = datetime.now(timezone.utc)
        view = PullRequestsView(current_user="gustavo-bertoglio")

        pr_gustavo = PullRequestItem(
            id=1, number=1, title="PR Gustavo", repo="org/repo",
            author="gustavo-bertoglio", author_avatar="", html_url="url1", created_at=now
        )
        pr_antonio = PullRequestItem(
            id=2, number=2, title="PR Antonio", repo="org/repo",
            author="antonio-fiscalmax", author_avatar="", html_url="url2", created_at=now
        )

        self.assertTrue(view._is_own_pr(pr_gustavo))
        self.assertFalse(view._is_own_pr(pr_antonio))

        # Altera usuário dinamicamente
        view.set_current_user("antonio-fiscalmax")
        self.assertFalse(view._is_own_pr(pr_gustavo))
        self.assertTrue(view._is_own_pr(pr_antonio))

    def test_pr_card_fixed_height(self):
        from src.ui.widgets.pr_card import PullRequestCard
        now = datetime.now(timezone.utc)
        pr = PullRequestItem(
            id=1, number=10, title="PR Teste Altura Fixa", repo="org/repo",
            author="dev", author_avatar="", html_url="url1", created_at=now
        )
        card = PullRequestCard(pr)
        self.assertEqual(card.minimumHeight(), 67)
        self.assertEqual(card.maximumHeight(), 67)

    def test_scroll_area_scrollbar_activation_when_exceeding_screen(self):
        from src.ui.views.prs_view import PullRequestsView
        now = datetime.now(timezone.utc)
        view = PullRequestsView()
        view.resize(800, 450)
        view.show()

        prs = [
            PullRequestItem(
                id=i, number=100 + i, title=f"PR {i}", repo="org/repo",
                author="dev", author_avatar="", html_url=f"url{i}", created_at=now
            )
            for i in range(15)
        ]
        view.update_prs(prs)
        self.app.processEvents()

        # Com 15 cards de 67px (total ~1000px), a barra de rolagem deve ter alcance positivo
        v_bar = view.scroll_area.verticalScrollBar()
        self.assertGreater(v_bar.maximum(), 0)

        # Ao filtrar para apenas 1 item (não ultrapassa a tela), alcance deve ser 0
        view.search_input.setText("PR 14")
        self.app.processEvents()
        self.assertEqual(v_bar.maximum(), 0)

        # Ao limpar o filtro (volta a 15 itens), alcance deve ser positivo novamente
        view.search_input.clear()
        self.app.processEvents()
        self.assertGreater(v_bar.maximum(), 0)

    def test_pr_cards_not_stretching_with_few_items(self):
        from src.ui.views.prs_view import PullRequestsView
        now = datetime.now(timezone.utc)
        view = PullRequestsView()
        view.resize(1200, 800)
        view.show()

        # 2 itens: devem ter exatamente 67px cada e o frame total 134px
        prs2 = [
            PullRequestItem(
                id=i, number=100 + i, title=f"PR {i}", repo="org/repo",
                author="dev", author_avatar="", html_url=f"url{i}", created_at=now
            )
            for i in range(2)
        ]
        view.update_prs(prs2)
        self.app.processEvents()

        self.assertEqual(view.prs_frame.height(), 134)
        for i in range(view.cards_layout.count()):
            card = view.cards_layout.itemAt(i).widget()
            self.assertEqual(card.height(), 67)

        # 7 itens: devem ter exatamente 67px cada e o frame total 469px
        prs7 = [
            PullRequestItem(
                id=i, number=200 + i, title=f"PR {i}", repo="org/repo",
                author="dev", author_avatar="", html_url=f"url{i}", created_at=now
            )
            for i in range(7)
        ]
        view.update_prs(prs7)
        self.app.processEvents()

        self.assertEqual(view.prs_frame.height(), 469)
        for i in range(view.cards_layout.count()):
            card = view.cards_layout.itemAt(i).widget()
            self.assertEqual(card.height(), 67)


if __name__ == "__main__":
    unittest.main()


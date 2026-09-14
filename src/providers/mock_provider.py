"""
Provedor de demonstração (Mock) com dados simulados para testes visuais.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from ..core.models import PullRequestItem
from .base import BaseStatusProvider


class MockProvider(BaseStatusProvider):
    def __init__(self, sort_order: str = "oldest_first", current_user: str = "antonio-fiscalmax"):
        self.sort_order = sort_order
        self.current_user = current_user
        self._cycle = 0

    def fetch(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        self._cycle += 1

        items: List[PullRequestItem] = [
            PullRequestItem(
                id=1080,
                number=1080,
                title="promote(FF-522,FF-523,FF-560,FF-561,FF-562,FF-563): rc-homolog",
                repo="Fiscalmax/api-monorepo",
                author="antonio-fiscalmax",
                author_avatar="",
                html_url="https://github.com",
                created_at=now - timedelta(days=7),
                updated_at=now - timedelta(days=7),
                is_draft=False,
                labels=["promote", "rc-homolog"],
                comments_count=0,
                review_decision=None,
                checks_summary="3/3",
                checks_state="SUCCESS"
            ),
            PullRequestItem(
                id=1079,
                number=1079,
                title="chore: incrementa versao do projeto no sonar [skip ci]",
                repo="Fiscalmax/api-monorepo",
                author="matheus-furiatto-FiscalMax",
                author_avatar="",
                html_url="https://github.com",
                created_at=now - timedelta(days=7),
                updated_at=now - timedelta(days=7),
                is_draft=False,
                labels=["chore", "sonar"],
                comments_count=0,
                review_decision="REVIEW_REQUIRED",
                checks_summary=None,
                checks_state=None
            ),
            PullRequestItem(
                id=1078,
                number=1078,
                title="fix/ff-522-manter-selecao-ao-paginar",
                repo="Fiscalmax/front-client",
                author="antonio-fiscalmax",
                author_avatar="",
                html_url="https://github.com",
                created_at=now - timedelta(days=7),
                updated_at=now - timedelta(days=7),
                is_draft=False,
                labels=["bugfix", "paginacao"],
                comments_count=2,
                review_decision="APPROVED",
                checks_summary="6/6",
                checks_state="SUCCESS"
            )
        ]

        # Simula nova PR surgindo no 2º ciclo para demonstrar notificação
        new_items = []
        if self._cycle > 1:
            new_pr = PullRequestItem(
                id=105,
                number=515,
                title="Hotfix: Atualização de dependências críticas de segurança",
                repo="Fiscalmax/api-monorepo",
                author="ana-sec",
                author_avatar="",
                html_url="https://github.com",
                created_at=now - timedelta(minutes=5),
                is_draft=False,
                labels=["hotfix", "security"],
                comments_count=0,
                review_decision="REVIEW_REQUIRED"
            )
            items.append(new_pr)
            new_items.append(new_pr)

        reverse = (self.sort_order == "newest_first")
        items.sort(key=lambda pr: pr.created_at, reverse=reverse)

        return {
            "items": items,
            "new_items": new_items,
            "errors": [],
            "current_user": self.current_user
        }

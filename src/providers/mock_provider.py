"""
Provedor de demonstração (Mock) com dados simulados para testes visuais.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from ..core.models import PullRequestItem
from .base import BaseStatusProvider


class MockProvider(BaseStatusProvider):
    def __init__(self, sort_order: str = "oldest_first"):
        self.sort_order = sort_order
        self._cycle = 0

    def fetch(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        self._cycle += 1

        items: List[PullRequestItem] = [
            PullRequestItem(
                id=101,
                number=142,
                title="Refatorar camada de autenticação JWT e migrar tokens para HTTP-only cookies",
                repo="sua-empresa/backend",
                author="carlos-dev",
                author_avatar="",
                html_url="https://github.com",
                created_at=now - timedelta(days=16),
                is_draft=False,
                labels=["segurança", "backend", "precisa-revisao"],
                comments_count=7,
                review_decision="REVIEW_REQUIRED"
            ),
            PullRequestItem(
                id=102,
                number=89,
                title="Corrigir memory leak no worker de processamento assíncrono em background",
                repo="sua-empresa/core",
                author="mariana-s",
                author_avatar="",
                html_url="https://github.com",
                created_at=now - timedelta(days=6),
                is_draft=False,
                labels=["bug", "performance"],
                comments_count=3,
                review_decision="CHANGES_REQUESTED"
            ),
            PullRequestItem(
                id=103,
                number=304,
                title="Adicionar suporte a notificações nativas do GNOME no Debian Linux",
                repo="sua-empresa/desktop-widgets",
                author="voce",
                author_avatar="",
                html_url="https://github.com",
                created_at=now - timedelta(days=2),
                is_draft=False,
                labels=["enhancement", "linux", "gnome"],
                comments_count=1,
                review_decision="APPROVED"
            ),
            PullRequestItem(
                id=104,
                number=512,
                title="Implementar suite de testes de integração ponta a ponta (E2E)",
                repo="sua-empresa/frontend",
                author="lucas-qa",
                author_avatar="",
                html_url="https://github.com",
                created_at=now - timedelta(hours=3),
                is_draft=True,
                labels=["testes", "qa", "draft"],
                comments_count=0,
                review_decision=None
            )
        ]

        # Simula nova PR surgindo no 2º ciclo para demonstrar notificação
        new_items = []
        if self._cycle > 1:
            new_pr = PullRequestItem(
                id=105,
                number=515,
                title="Hotfix: Atualização de dependências críticas de segurança",
                repo="sua-empresa/backend",
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
            "errors": []
        }

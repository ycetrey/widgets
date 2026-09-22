"""
Testes automatizados para a renderização de PDF do Relatório de Sprint Freeze.
"""
import os
import unittest
from datetime import datetime, timezone

from src.core.models import SprintFreezeReport, SprintFreezeTaskEntry


class TestPdfReport(unittest.TestCase):
    def test_render_report_pdf_creates_valid_pdf_file(self):
        from src.core.pdf_report import render_report_pdf

        tmp_path = "tests_tmp_freeze_report.pdf"
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        try:
            report = SprintFreezeReport(
                id=0,
                sprint_id="10",
                sprint_name="Sprint 42",
                generated_at=datetime.now(timezone.utc),
                is_automatic=False,
                total_tasks=2,
                promoted_count=1,
                retained_count=1,
                pdf_path="",
                retained_tasks=[
                    SprintFreezeTaskEntry(
                        key="FF-100",
                        summary="Ajustar tela de cenários",
                        assignee="Antonio Barbosa",
                        jira_status="QA",
                        html_url="https://jira.com/FF-100",
                        diagnosis="🧪 QA",
                        pr_url=None
                    )
                ]
            )

            result_path = render_report_pdf(report, tmp_path)

            self.assertEqual(result_path, tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, "rb") as f:
                header = f.read(5)
            self.assertEqual(header, b"%PDF-")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_render_report_pdf_handles_empty_retained_list(self):
        from src.core.pdf_report import render_report_pdf

        tmp_path = "tests_tmp_freeze_report_empty.pdf"
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        try:
            report = SprintFreezeReport(
                id=0, sprint_id="11", sprint_name="Sprint 43",
                generated_at=datetime.now(timezone.utc), is_automatic=True,
                total_tasks=5, promoted_count=5, retained_count=0, pdf_path=""
            )
            render_report_pdf(report, tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

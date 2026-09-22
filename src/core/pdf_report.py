"""
Renderização do Relatório de Sprint Freeze em PDF, a partir de um HTML
estilizado (mesmo layout usado no relatório de referência do time).
"""
import html

from .models import SprintFreezeReport, SprintFreezeTaskEntry

_REPORT_CSS = """
body { font-family: 'DejaVu Sans', Arial, sans-serif; color: #1e1e2e; margin: 32px; }
h1 { color: #1e40af; font-size: 20px; }
h2 { color: #1e293b; font-size: 15px; margin-top: 24px; }
table { width: 100%; border-collapse: collapse; margin-top: 12px; }
th, td { border: 1px solid #cbd5e1; padding: 8px; font-size: 12px; text-align: left; }
th { background-color: #1e40af; color: #ffffff; }
tr:nth-child(even) { background-color: #f1f5f9; }
.summary { background-color: #eff6ff; border-radius: 6px; padding: 12px 16px; margin-top: 8px; }
"""


def _render_row(task: SprintFreezeTaskEntry) -> str:
    pr_cell = f'<a href="{html.escape(task.pr_url)}">Ver PR</a>' if task.pr_url else "—"
    return (
        f"<tr><td>{html.escape(task.key)}</td><td>{html.escape(task.summary)}</td>"
        f"<td>{html.escape(task.assignee)}</td><td>{html.escape(task.jira_status)}</td>"
        f"<td>{html.escape(task.diagnosis)}</td><td>{pr_cell}</td></tr>"
    )


def _render_html(report: SprintFreezeReport) -> str:
    rows = "".join(_render_row(task) for task in report.retained_tasks)
    if not rows:
        rows = '<tr><td colspan="6">Nenhuma tarefa retida — sprint 100% promovida! 🎉</td></tr>'

    generated_str = report.generated_at.astimezone().strftime("%d/%m/%Y %H:%M")

    return f"""
    <html>
    <head><meta charset="utf-8"><style>{_REPORT_CSS}</style></head>
    <body>
        <h1>📊 Relatório de Sprint Freeze — {html.escape(report.sprint_name)}</h1>
        <p>Gerado em {generated_str}</p>
        <p style="color:#64748b;font-size:11px;">Escopo: tarefas retornadas pela consulta JQL configurada no widget (pode não refletir 100% da sprint se a consulta for filtrada por responsável).</p>
        <div class="summary">
            <strong>Total de tarefas:</strong> {report.total_tasks}<br>
            <strong>Promovidas para produção:</strong> {report.promoted_count}<br>
            <strong>Retidas no Freeze Time:</strong> {report.retained_count}
        </div>
        <h2>📋 Tarefas Retidas no Freeze Time</h2>
        <table>
            <tr><th>Chave</th><th>Título</th><th>Responsável</th><th>Status Jira</th><th>Diagnóstico</th><th>PR</th></tr>
            {rows}
        </table>
    </body>
    </html>
    """


def render_report_pdf(report: SprintFreezeReport, output_path: str) -> str:
    """
    Renderiza o relatório em PDF no caminho informado e retorna o próprio caminho.

    Tenta primeiramente via WeasyPrint (layout CSS avançado).
    Se WeasyPrint não estiver disponível (ex: no Windows sem libs GTK3/Pango instaladas),
    utiliza como fallback o motor nativo de PDF do PyQt6 (QPdfWriter + QTextDocument).
    """
    html_content = _render_html(report)

    # 1. Tenta via WeasyPrint
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return output_path
    except Exception as weasy_err:
        # 2. Fallback para motor de PDF nativo do PyQt6 (dispensa dependências C externas)
        try:
            from PyQt6.QtCore import QMarginsF
            from PyQt6.QtGui import QPageSize, QPdfWriter, QTextDocument
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                app = QApplication(["dev-status-widget", "-platform", "offscreen"])

            doc = QTextDocument()
            doc.setHtml(html_content)
            writer = QPdfWriter(output_path)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageMargins(QMarginsF(15, 15, 15, 15))
            doc.print(writer)
            return output_path
        except Exception as qt_err:
            raise RuntimeError(
                f"Falha ao renderizar PDF via WeasyPrint ({weasy_err}) e via Qt ({qt_err})"
            )

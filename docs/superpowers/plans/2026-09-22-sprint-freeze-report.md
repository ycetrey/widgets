# Relatório de Sprint Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar ao Dev Status Widget um botão + aba "🧊 Freeze" que gera (manualmente ou automaticamente às segundas-feiras de virada de sprint) um relatório em PDF das tarefas do Jira que não chegaram em produção, cruzando status do Jira com PRs de promoção no GitHub.

**Architecture:** Segue o padrão Provider → Service → View → Database já usado no projeto. `JiraProvider` e `GitHubProvider` ganham métodos novos (sprint ativa e busca de PRs de promoção); um módulo novo `sprint_freeze.py` orquestra o cruzamento e a geração; `pdf_report.py` renderiza o PDF via WeasyPrint; uma nova tabela SQLite guarda o histórico; uma nova aba/view lista os relatórios com botão de download. A checagem automática de segunda-feira reaproveita o mecanismo de `QTimer` já usado pelo refresh de PRs/Jira, sem scheduler externo.

**Tech Stack:** Python 3.11, PyQt6, requests, WeasyPrint (novo), SQLite (stdlib `sqlite3`), `unittest` + `unittest.mock` para testes.

**Spec:** `docs/superpowers/specs/2026-09-22-sprint-freeze-report-design.md`

## Global Constraints

- Nunca fazer commit automático (regra global do usuário, CLAUDE.md) — cada tarefa termina com o diff pronto para revisão, não com `git commit`. Só commitar se o usuário pedir explicitamente naquele momento.
- Não rodar lint automaticamente após Write/Edit — só quando o usuário pedir.
- Rodar testes com `python3 -m unittest ... -v` (pytest não está instalado neste ambiente e não deve ser adicionado só para isso; `unittest` já suporta `-k` para filtrar por nome/substring, inclusive múltiplos `-k` combinados como OR). Sem paralelismo.
- `freeze_production_branch` tem padrão `"rc-prod"`.
- A aba "🧊 Freeze" só é visível se `freeze_reports_enabled=True` **e** `jira_enabled=True`.
- PDF é gerado via WeasyPrint (HTML → PDF), não ReportLab.
- Diagnóstico de tarefa retida usa o status literal do Jira (sem inferir "Dev" vs "QA" por nome de subtarefa).
- Geração manual pode repetir para a mesma sprint; a geração automática só roda uma vez por `sprint_id` (checado via consulta no banco, sem `UNIQUE` constraint).
- Preservar exatamente o estilo de código existente (docstrings/comentários em português, paleta de cores dark já usada nos outros widgets/views).

---

## File Structure

**Novos arquivos:**
- `src/core/sprint_freeze.py` — `build_report()`, `should_generate_automatic_report()`, `default_reports_dir()`, `generate_and_save()`.
- `src/core/pdf_report.py` — `render_report_pdf()`.
- `src/ui/widgets/freeze_report_card.py` — `FreezeReportCard`.
- `src/ui/views/freeze_report_view.py` — `FreezeReportView`.
- `tests/test_sprint_freeze.py` — testes do serviço + widgets de UI da feature.
- `tests/test_pdf_report.py` — testes da renderização de PDF.

**Arquivos modificados:**
- `src/core/models.py` — `AppConfig` (2 campos novos), `JiraSprintInfo`, `SprintFreezeTaskEntry`, `SprintFreezeReport`.
- `src/core/config.py` — load/save dos 2 campos novos.
- `config.example.yaml` — documentação dos 2 campos novos.
- `src/core/database.py` — tabela `freeze_reports` + 3 métodos novos.
- `src/providers/jira_provider.py` — `get_active_sprint()`.
- `src/providers/github_provider.py` — `search_promotion_prs()`.
- `requirements.txt` — adiciona `weasyprint`.
- `install.sh` — adiciona libs de sistema do WeasyPrint.
- `src/ui/views/settings_view.py` — novo grupo de configuração.
- `src/ui/main_window.py` — nova aba, worker de geração, botão manual, timer de checagem automática.
- `tests/test_widget.py` — testes de `TestConfigManager`, `TestCoreModels`, `TestGitHubProviderPromotionSearch`, `TestSettingsView`.
- `tests/test_jira.py` — testes de `get_active_sprint()`.
- `tests/test_database.py` — testes de `freeze_reports`.

---

### Task 1: Modelos e configuração (AppConfig + dataclasses novos)

**Files:**
- Modify: `src/core/models.py`
- Modify: `src/core/config.py`
- Modify: `config.example.yaml`
- Test: `tests/test_widget.py`

**Interfaces:**
- Produces: `AppConfig.freeze_reports_enabled: bool`, `AppConfig.freeze_production_branch: str`; `JiraSprintInfo(id: int, name: str, start_date: Optional[datetime], end_date: Optional[datetime])`; `SprintFreezeTaskEntry(key, summary, assignee, jira_status, html_url, diagnosis, pr_url=None)`; `SprintFreezeReport(id, sprint_id, sprint_name, generated_at, is_automatic, total_tasks, promoted_count, retained_count, pdf_path, retained_tasks=[])`.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar em `tests/test_widget.py`, dentro de `class TestCoreModels`, um novo método:

```python
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
```

E, dentro de `class TestConfigManager`, um novo método:

```python
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
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

Run: `python3 -m unittest tests.test_widget -k sprint_freeze_dataclasses_defaults -k freeze_report_config_roundtrip -v`
Expected: FAIL (`ImportError` / `AttributeError`, pois os campos e classes ainda não existem).

- [ ] **Step 3: Implementar em `src/core/models.py`**

Logo após a classe `JiraTaskItem` (antes de `AppConfig`), adicionar:

```python
@dataclass
class JiraSprintInfo:
    id: int
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
```

Dentro de `AppConfig`, logo após `autostart: bool = False`, adicionar:

```python

    # Relatório de Sprint Freeze
    freeze_reports_enabled: bool = False
    freeze_production_branch: str = "rc-prod"
```

Logo após a classe `AppConfig` (antes de `NotificationItem`), adicionar:

```python
@dataclass
class SprintFreezeTaskEntry:
    key: str
    summary: str
    assignee: str
    jira_status: str
    html_url: str
    diagnosis: str
    pr_url: Optional[str] = None


@dataclass
class SprintFreezeReport:
    id: int
    sprint_id: str
    sprint_name: str
    generated_at: datetime
    is_automatic: bool
    total_tasks: int
    promoted_count: int
    retained_count: int
    pdf_path: str
    retained_tasks: List[SprintFreezeTaskEntry] = field(default_factory=list)
```

- [ ] **Step 4: Implementar em `src/core/config.py`**

No método `load()`, o `return AppConfig(...)` termina hoje com `autostart=bool(data.get("autostart", False))`. Alterar para:

```python
                autostart=bool(data.get("autostart", False)),
                freeze_reports_enabled=bool(data.get("freeze_reports_enabled", False)),
                freeze_production_branch=str(data.get("freeze_production_branch") or "rc-prod").strip()
            )
```

No método `save()`, o dicionário `data` termina hoje com `"autostart": self.config.autostart`. Alterar para:

```python
                "autostart": self.config.autostart,
                "freeze_reports_enabled": self.config.freeze_reports_enabled,
                "freeze_production_branch": self.config.freeze_production_branch
            }
```

- [ ] **Step 5: Atualizar `config.example.yaml`**

Adicionar ao final do arquivo:

```yaml

# ==============================================================================
# Relatório de Sprint Freeze (Opcional, requer jira_enabled: true)
# ==============================================================================
# Habilita a aba "🧊 Freeze" e a geração automática de relatório toda
# segunda-feira em que a sprint ativa já passou da data de término.
freeze_reports_enabled: false

# Branch de destino que caracteriza uma PR como "promovida para produção"
freeze_production_branch: "rc-prod"
```

- [ ] **Step 6: Rodar os testes e confirmar que passam**

Run: `python3 -m unittest tests.test_widget -k sprint_freeze_dataclasses_defaults -k freeze_report_config_roundtrip -v`
Expected: PASS

- [ ] **Step 7: Revisar o diff (sem commit automático — só commitar se o usuário pedir explicitamente)**

---

### Task 2: Persistência — tabela `freeze_reports`

**Files:**
- Modify: `src/core/database.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: `SprintFreezeReport` (Task 1).
- Produces: `DatabaseManager.save_freeze_report(report: SprintFreezeReport) -> int`, `DatabaseManager.get_freeze_reports() -> List[SprintFreezeReport]`, `DatabaseManager.has_automatic_freeze_report(sprint_id: str) -> bool`.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar em `tests/test_database.py`:

```python
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
        from src.core.models import SprintFreezeReport

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
        from src.core.models import SprintFreezeReport

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
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

Run: `python3 -m unittest tests.test_database -k FreezeReportsDatabase -v`
Expected: FAIL (`AttributeError: 'DatabaseManager' object has no attribute 'save_freeze_report'`)

- [ ] **Step 3: Implementar em `src/core/database.py`**

No topo do arquivo, atualizar o import:

```python
from .models import JiraTaskItem, NotificationItem, PullRequestItem, SprintFreezeReport
```

Dentro de `_init_db()`, logo após o bloco `CREATE INDEX IF NOT EXISTS idx_notifications_dismissed_created ...` e antes do `conn.commit()` final, adicionar:

```python

            conn.execute("""
                CREATE TABLE IF NOT EXISTS freeze_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sprint_id TEXT NOT NULL,
                    sprint_name TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    is_automatic INTEGER DEFAULT 0,
                    total_tasks INTEGER NOT NULL,
                    promoted_count INTEGER NOT NULL,
                    retained_count INTEGER NOT NULL,
                    pdf_path TEXT NOT NULL
                )
            """)
```

No final da classe `DatabaseManager` (após `dismiss_all_notifications`), adicionar:

```python

    def save_freeze_report(self, report: SprintFreezeReport) -> int:
        now_iso = report.generated_at.isoformat() if report.generated_at else datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO freeze_reports (
                    sprint_id, sprint_name, generated_at, is_automatic,
                    total_tasks, promoted_count, retained_count, pdf_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.sprint_id,
                report.sprint_name,
                now_iso,
                1 if report.is_automatic else 0,
                report.total_tasks,
                report.promoted_count,
                report.retained_count,
                report.pdf_path
            ))
            conn.commit()
            return cursor.lastrowid

    def get_freeze_reports(self) -> List[SprintFreezeReport]:
        items: List[SprintFreezeReport] = []
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM freeze_reports ORDER BY generated_at DESC")
            for row in cursor.fetchall():
                items.append(SprintFreezeReport(
                    id=row["id"],
                    sprint_id=row["sprint_id"],
                    sprint_name=row["sprint_name"],
                    generated_at=self._parse_iso(row["generated_at"]) or datetime.now(timezone.utc),
                    is_automatic=bool(row["is_automatic"]),
                    total_tasks=row["total_tasks"],
                    promoted_count=row["promoted_count"],
                    retained_count=row["retained_count"],
                    pdf_path=row["pdf_path"]
                ))
        return items

    def has_automatic_freeze_report(self, sprint_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM freeze_reports WHERE sprint_id = ? AND is_automatic = 1 LIMIT 1",
                (str(sprint_id),)
            )
            return cursor.fetchone() is not None
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python3 -m unittest tests.test_database -k FreezeReportsDatabase -v`
Expected: PASS

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

### Task 3: `JiraProvider.get_active_sprint()`

**Files:**
- Modify: `src/providers/jira_provider.py`
- Test: `tests/test_jira.py`

**Interfaces:**
- Consumes: `JiraSprintInfo` (Task 1).
- Produces: `JiraProvider.get_active_sprint(sample_task_key: str) -> Optional[JiraSprintInfo]`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_jira.py`, atualizar a linha de import existente `from src.core.models import JiraTaskItem, AppConfig` para incluir `JiraSprintInfo`:

```python
from src.core.models import AppConfig, JiraSprintInfo, JiraTaskItem
```

Depois, adicionar ao final do arquivo:

```python
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
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

Run: `python3 -m unittest tests.test_jira -k ActiveSprint -v`
Expected: FAIL (`AttributeError: 'JiraProvider' object has no attribute 'get_active_sprint'`)

- [ ] **Step 3: Implementar em `src/providers/jira_provider.py`**

No topo do arquivo, atualizar o import de modelos:

```python
from ..core.models import JiraSprintInfo, JiraTaskItem
```

No final da classe `JiraProvider` (após o método `_fetch_mock_data`), adicionar:

```python

    def get_active_sprint(self, sample_task_key: str) -> Optional[JiraSprintInfo]:
        """
        Descobre a sprint ativa do board correspondente ao projeto de
        `sample_task_key` (ex: "FF-1234" -> projeto "FF") usando a API Agile
        do Jira. Retorna None se estiver em modo demo, faltar credenciais,
        ou não houver board/sprint ativa encontrados.
        """
        if self.demo_mode or not (self.jira_url and self.email and self.api_token):
            return None
        if not sample_task_key or "-" not in sample_task_key:
            return None

        project_key = sample_task_key.split("-", 1)[0]
        headers = {
            "Accept": "application/json",
            "User-Agent": "DevStatusWidget-Debian/1.0"
        }
        auth = HTTPBasicAuth(self.email, self.api_token)

        try:
            board_resp = requests.get(
                f"{self.jira_url}/rest/agile/1.0/board",
                headers=headers, auth=auth,
                params={"projectKeyOrId": project_key},
                timeout=12
            )
            if board_resp.status_code != 200:
                return None
            boards = board_resp.json().get("values", [])
            if not boards:
                return None
            board_id = boards[0]["id"]

            sprint_resp = requests.get(
                f"{self.jira_url}/rest/agile/1.0/board/{board_id}/sprint",
                headers=headers, auth=auth,
                params={"state": "active"},
                timeout=12
            )
            if sprint_resp.status_code != 200:
                return None
            sprints = sprint_resp.json().get("values", [])
            if not sprints:
                return None

            sprint = sprints[0]
            return JiraSprintInfo(
                id=sprint["id"],
                name=sprint.get("name", ""),
                start_date=self._parse_datetime(sprint["startDate"]) if sprint.get("startDate") else None,
                end_date=self._parse_datetime(sprint["endDate"]) if sprint.get("endDate") else None
            )
        except requests.exceptions.RequestException:
            return None
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python3 -m unittest tests.test_jira -k ActiveSprint -v`
Expected: PASS

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

### Task 4: `GitHubProvider.search_promotion_prs()`

**Files:**
- Modify: `src/providers/github_provider.py`
- Test: `tests/test_widget.py`

**Interfaces:**
- Produces: `GitHubProvider.search_promotion_prs(task_keys: List[str], base_branch: str) -> Tuple[Dict[str, dict], bool]` — retorna `({chave: {"merged": bool, "pr_url": str}}, houve_erro)`; `houve_erro=True` se alguma consulta falhou (rate limit, token inválido, erro de rede), para o chamador sinalizar tarefas não verificadas em vez de assumir "sem PR".

- [ ] **Step 1: Escrever os testes que falham**

Adicionar em `tests/test_widget.py`:

```python
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
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

Run: `python3 -m unittest tests.test_widget -k PromotionSearch -v`
Expected: FAIL (`AttributeError: 'GitHubProvider' object has no attribute 'search_promotion_prs'`)

- [ ] **Step 3: Implementar em `src/providers/github_provider.py`**

No final da classe `GitHubProvider` (após o método `fetch`), adicionar:

```python

    def search_promotion_prs(self, task_keys: List[str], base_branch: str) -> Tuple[Dict[str, dict], bool]:
        """
        Busca PRs (abertas ou mescladas) cujo título contenha alguma das
        chaves informadas e cuja branch de destino seja `base_branch`, via
        a GitHub Search Issues API. Retorna uma tupla (resultados, houve_erro):
        resultados no formato {chave: {"merged": bool, "pr_url": str}} apenas
        para as chaves em que uma PR correspondente foi encontrada (prioriza a
        PR mesclada quando houver mais de uma correspondência), e
        houve_erro=True se alguma consulta falhou (rate limit, token
        inválido, erro de rede) — para o chamador não confundir "sem PR"
        com "não foi possível verificar".
        """
        results: Dict[str, dict] = {}
        had_error = False
        if not task_keys or not self.repositories:
            return results, had_error

        headers = self._get_headers()
        unique_keys = list(dict.fromkeys(k.strip() for k in task_keys if k and k.strip()))

        for repo in self.repositories:
            repo_clean = repo.strip()
            if not repo_clean or "/" not in repo_clean:
                continue

            for chunk_start in range(0, len(unique_keys), 10):
                chunk = unique_keys[chunk_start:chunk_start + 10]
                key_query = " OR ".join(chunk)
                query = f"repo:{repo_clean} is:pr base:{base_branch} ({key_query})"

                try:
                    resp = requests.get(
                        f"{self.API_BASE}/search/issues",
                        headers=headers,
                        params={"q": query, "per_page": 50},
                        timeout=12
                    )
                except requests.exceptions.RequestException:
                    had_error = True
                    continue

                if resp.status_code != 200:
                    had_error = True
                    continue

                for item in resp.json().get("items", []):
                    title = item.get("title", "")
                    pr_info = item.get("pull_request") or {}
                    merged = pr_info.get("merged_at") is not None
                    pr_url = item.get("html_url", "")

                    for key in chunk:
                        if key in title and (key not in results or merged):
                            results[key] = {"merged": merged, "pr_url": pr_url}

        return results, had_error
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python3 -m unittest tests.test_widget -k PromotionSearch -v`
Expected: PASS

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

### Task 5: `sprint_freeze.build_report()` e `should_generate_automatic_report()`

**Files:**
- Create: `src/core/sprint_freeze.py`
- Test: `tests/test_sprint_freeze.py`

**Interfaces:**
- Consumes: `JiraTaskItem`, `JiraSprintInfo`, `SprintFreezeReport`, `SprintFreezeTaskEntry` (Task 1); resultado de `search_promotion_prs()` (Task 4, formato `Dict[str, dict]` + flag de erro).
- Produces: `build_report(jira_tasks: List[JiraTaskItem], sprint_info: JiraSprintInfo, promotion_status: dict, is_automatic: bool = False, github_search_failed: bool = False) -> SprintFreezeReport`; `should_generate_automatic_report(today: date, sprint_end_date: Optional[datetime], already_has_automatic: bool) -> bool`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_sprint_freeze.py`:

```python
"""
Testes automatizados para o serviço de Relatório de Sprint Freeze.
"""
import unittest
from datetime import date, datetime, timedelta, timezone

from src.core.models import JiraSprintInfo, JiraTaskItem


def _make_task(key, status, status_category, is_subtask=False):
    now = datetime.now(timezone.utc)
    return JiraTaskItem(
        key=key,
        summary=f"Tarefa {key}",
        status=status,
        status_category=status_category,
        priority="Média",
        issue_type="Tarefa",
        assignee="Dev",
        created_at=now,
        updated_at=now,
        html_url=f"https://jira.com/{key}",
        is_subtask=is_subtask
    )


class TestBuildReport(unittest.TestCase):
    def setUp(self):
        from src.core.sprint_freeze import build_report
        self.build_report = build_report
        self.sprint_info = JiraSprintInfo(
            id=42, name="Sprint 42",
            start_date=datetime.now(timezone.utc) - timedelta(days=14),
            end_date=datetime.now(timezone.utc)
        )

    def test_merged_pr_counts_as_promoted(self):
        tasks = [_make_task("FF-1", "Concluído", "done")]
        promotion_status = {"FF-1": {"merged": True, "pr_url": "https://github.com/org/repo/pull/1"}}

        report = self.build_report(tasks, self.sprint_info, promotion_status)

        self.assertEqual(report.promoted_count, 1)
        self.assertEqual(report.retained_count, 0)
        self.assertEqual(report.retained_tasks, [])

    def test_open_pr_is_retained_with_pr_diagnosis(self):
        tasks = [_make_task("FF-2", "Em Progresso", "indeterminate")]
        promotion_status = {"FF-2": {"merged": False, "pr_url": "https://github.com/org/repo/pull/2"}}

        report = self.build_report(tasks, self.sprint_info, promotion_status)

        self.assertEqual(report.retained_count, 1)
        self.assertEqual(report.retained_tasks[0].diagnosis, "⚠️ PR aberta aguardando merge")
        self.assertEqual(report.retained_tasks[0].pr_url, "https://github.com/org/repo/pull/2")

    def test_no_pr_uses_jira_status_as_diagnosis(self):
        tasks = [_make_task("FF-3", "A Fazer", "new")]
        report = self.build_report(tasks, self.sprint_info, {})

        self.assertEqual(report.retained_count, 1)
        self.assertEqual(report.retained_tasks[0].diagnosis, "🔨 A Fazer")
        self.assertIsNone(report.retained_tasks[0].pr_url)

    def test_subtasks_are_excluded_from_report(self):
        tasks = [
            _make_task("FF-4", "A Fazer", "new"),
            _make_task("FF-4-SUB1", "A Fazer", "new", is_subtask=True)
        ]
        report = self.build_report(tasks, self.sprint_info, {})

        self.assertEqual(report.total_tasks, 1)

    def test_github_search_failure_marks_diagnosis_as_unverified(self):
        tasks = [_make_task("FF-5", "A Fazer", "new")]
        report = self.build_report(tasks, self.sprint_info, {}, github_search_failed=True)

        self.assertEqual(report.retained_tasks[0].diagnosis, "❔ Não foi possível verificar PR")


class TestShouldGenerateAutomaticReport(unittest.TestCase):
    MONDAY = date(2024, 1, 1)   # 2024-01-01 é uma segunda-feira
    TUESDAY = date(2024, 1, 2)

    def setUp(self):
        from src.core.sprint_freeze import should_generate_automatic_report
        self.should_generate = should_generate_automatic_report

    def test_generates_on_freeze_monday(self):
        sprint_end = datetime(2023, 12, 31, tzinfo=timezone.utc)
        self.assertTrue(self.should_generate(self.MONDAY, sprint_end, already_has_automatic=False))

    def test_skips_if_already_generated(self):
        sprint_end = datetime(2023, 12, 31, tzinfo=timezone.utc)
        self.assertFalse(self.should_generate(self.MONDAY, sprint_end, already_has_automatic=True))

    def test_skips_on_non_monday(self):
        sprint_end = datetime(2023, 12, 31, tzinfo=timezone.utc)
        self.assertFalse(self.should_generate(self.TUESDAY, sprint_end, already_has_automatic=False))

    def test_skips_if_sprint_not_ended_yet(self):
        sprint_end = datetime(2024, 1, 5, tzinfo=timezone.utc)
        self.assertFalse(self.should_generate(self.MONDAY, sprint_end, already_has_automatic=False))

    def test_skips_if_no_sprint_end_date(self):
        self.assertFalse(self.should_generate(self.MONDAY, None, already_has_automatic=False))
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

Run: `python3 -m unittest tests.test_sprint_freeze -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.core.sprint_freeze'`)

- [ ] **Step 3: Implementar `src/core/sprint_freeze.py`**

```python
"""
Serviço de geração do Relatório de Sprint Freeze: cruza tarefas do Jira com
PRs de promoção no GitHub para identificar o que não chegou em produção.
"""
from datetime import date, datetime, timezone
from typing import List, Optional

from .models import JiraSprintInfo, JiraTaskItem, SprintFreezeReport, SprintFreezeTaskEntry

STATUS_CATEGORY_EMOJI = {
    "new": "🔨",
    "indeterminate": "🧪",
    "done": "✅",
}


def build_report(
    jira_tasks: List[JiraTaskItem],
    sprint_info: JiraSprintInfo,
    promotion_status: dict,
    is_automatic: bool = False,
    github_search_failed: bool = False,
) -> SprintFreezeReport:
    """
    Monta o SprintFreezeReport a partir das tarefas da sprint (apenas as que
    não são subtarefas), da sprint ativa e do resultado de
    `GitHubProvider.search_promotion_prs()` (dict {chave: {"merged": bool, "pr_url": str}}).
    Se `github_search_failed=True`, tarefas sem PR encontrada recebem o
    diagnóstico "não foi possível verificar" em vez do status do Jira, para
    não conflitar "sem PR" com "falha ao consultar o GitHub".
    """
    top_level_tasks = [t for t in jira_tasks if not t.is_subtask]
    retained: List[SprintFreezeTaskEntry] = []
    promoted_count = 0

    for task in top_level_tasks:
        promo = promotion_status.get(task.key)

        if promo and promo.get("merged"):
            promoted_count += 1
            continue

        if promo and not promo.get("merged"):
            diagnosis = "⚠️ PR aberta aguardando merge"
            pr_url = promo.get("pr_url")
        elif github_search_failed:
            diagnosis = "❔ Não foi possível verificar PR"
            pr_url = None
        else:
            emoji = STATUS_CATEGORY_EMOJI.get(task.status_category, "🔎")
            diagnosis = f"{emoji} {task.status}"
            pr_url = None

        retained.append(SprintFreezeTaskEntry(
            key=task.key,
            summary=task.summary,
            assignee=task.assignee,
            jira_status=task.status,
            html_url=task.html_url,
            diagnosis=diagnosis,
            pr_url=pr_url
        ))

    return SprintFreezeReport(
        id=0,
        sprint_id=str(sprint_info.id),
        sprint_name=sprint_info.name,
        generated_at=datetime.now(timezone.utc),
        is_automatic=is_automatic,
        total_tasks=len(top_level_tasks),
        promoted_count=promoted_count,
        retained_count=len(retained),
        pdf_path="",
        retained_tasks=retained
    )


def should_generate_automatic_report(
    today: date,
    sprint_end_date: Optional[datetime],
    already_has_automatic: bool,
) -> bool:
    """
    Decide se a checagem automática de segunda-feira deve gerar um novo
    relatório: precisa ser segunda-feira, a sprint ativa precisa já ter
    passado da data de término, e ainda não pode existir um relatório
    automático para essa sprint.
    """
    if already_has_automatic:
        return False
    if today.weekday() != 0:
        return False
    if sprint_end_date is None:
        return False
    return sprint_end_date.date() <= today
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python3 -m unittest tests.test_sprint_freeze -v`
Expected: PASS

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

### Task 6: `pdf_report.render_report_pdf()` + dependência WeasyPrint

**Files:**
- Create: `src/core/pdf_report.py`
- Modify: `requirements.txt`
- Modify: `install.sh`
- Test: `tests/test_pdf_report.py`

**Interfaces:**
- Consumes: `SprintFreezeReport`, `SprintFreezeTaskEntry` (Task 1).
- Produces: `render_report_pdf(report: SprintFreezeReport, output_path: str) -> str`.

- [ ] **Step 1: Adicionar a dependência**

Em `requirements.txt`, adicionar a linha:

```
weasyprint>=62.0
```

Em `install.sh`, no bloco `sudo apt-get install -y -qq \ ... `, adicionar as libs de sistema do WeasyPrint antes de `gnome-shell-extension-appindicator`:

```bash
        libnotify-bin \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libcairo2 \
        gnome-shell-extension-appindicator || {
```

Instalar localmente para poder rodar os testes deste ambiente de desenvolvimento:

Run: `pip3 install --user weasyprint`

- [ ] **Step 2: Escrever o teste que falha**

Criar `tests/test_pdf_report.py`:

```python
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
```

- [ ] **Step 3: Rodar o teste para confirmar que falha**

Run: `python3 -m unittest tests.test_pdf_report -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.core.pdf_report'`)

- [ ] **Step 4: Implementar `src/core/pdf_report.py`**

```python
"""
Renderização do Relatório de Sprint Freeze em PDF, a partir de um HTML
estilizado (mesmo layout usado no relatório de referência do time).
"""
from weasyprint import HTML

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
    pr_cell = f'<a href="{task.pr_url}">Ver PR</a>' if task.pr_url else "—"
    return (
        f"<tr><td>{task.key}</td><td>{task.summary}</td><td>{task.assignee}</td>"
        f"<td>{task.jira_status}</td><td>{task.diagnosis}</td><td>{pr_cell}</td></tr>"
    )


def _render_html(report: SprintFreezeReport) -> str:
    rows = "".join(_render_row(task) for task in report.retained_tasks)
    if not rows:
        rows = '<tr><td colspan="6">Nenhuma tarefa retida — sprint 100% promovida! 🎉</td></tr>'

    generated_str = report.generated_at.strftime("%d/%m/%Y %H:%M")

    return f"""
    <html>
    <head><meta charset="utf-8"><style>{_REPORT_CSS}</style></head>
    <body>
        <h1>📊 Relatório de Sprint Freeze — {report.sprint_name}</h1>
        <p>Gerado em {generated_str}</p>
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
    Renderiza o relatório em PDF no caminho informado e retorna o próprio
    caminho.
    """
    html_content = _render_html(report)
    HTML(string=html_content).write_pdf(output_path)
    return output_path
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `python3 -m unittest tests.test_pdf_report -v`
Expected: PASS

- [ ] **Step 6: Revisar o diff (sem commit automático)**

---

### Task 7: `sprint_freeze.generate_and_save()` (orquestração completa)

**Files:**
- Modify: `src/core/sprint_freeze.py`
- Modify: `tests/test_sprint_freeze.py`

**Interfaces:**
- Consumes: `JiraProvider.fetch()` (dict com `"items"`), `JiraProvider.get_active_sprint()` (Task 3), `GitHubProvider.search_promotion_prs()` (Task 4), `DatabaseManager.save_freeze_report()` (Task 2), `render_report_pdf()` (Task 6), `build_report()` (Task 5).
- Produces: `default_reports_dir() -> Path`; `generate_and_save(jira_provider, github_provider, db, production_branch: str, is_automatic: bool = False, reports_dir: Optional[Path] = None) -> Optional[SprintFreezeReport]`.

- [ ] **Step 1: Escrever os testes que falham**

No topo de `tests/test_sprint_freeze.py`, os testes desta task precisam de `os` (para o arquivo de banco temporário) e de `MagicMock`/`patch` (para simular providers), que a Task 5 não usou e por isso não importou. Atualizar o bloco de imports do topo do arquivo para:

```python
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.core.models import JiraSprintInfo, JiraTaskItem
```

Depois, adicionar ao final de `tests/test_sprint_freeze.py`:

```python
class TestGenerateAndSave(unittest.TestCase):
    def setUp(self):
        self.tmp_db = "tests_tmp_freeze_generate.db"
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)
        from src.core.database import DatabaseManager
        self.db = DatabaseManager(custom_path=self.tmp_db)

    def tearDown(self):
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)

    @patch("src.core.sprint_freeze.render_report_pdf")
    def test_generate_and_save_persists_report(self, mock_render_pdf):
        mock_render_pdf.side_effect = lambda report, path: path

        jira_provider = MagicMock()
        jira_provider.fetch.return_value = {
            "items": [_make_task("FF-9", "A Fazer", "new")],
            "new_items": [],
            "errors": []
        }
        jira_provider.get_active_sprint.return_value = JiraSprintInfo(
            id=99, name="Sprint 99", start_date=None, end_date=None
        )

        github_provider = MagicMock()
        github_provider.search_promotion_prs.return_value = ({}, False)

        from src.core.sprint_freeze import generate_and_save
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            report = generate_and_save(
                jira_provider, github_provider, self.db,
                production_branch="rc-prod",
                is_automatic=True,
                reports_dir=Path(tmp_dir)
            )

        self.assertIsNotNone(report)
        self.assertEqual(report.sprint_name, "Sprint 99")
        self.assertTrue(report.is_automatic)
        self.assertGreater(report.id, 0)

        stored = self.db.get_freeze_reports()
        self.assertEqual(len(stored), 1)
        self.assertTrue(self.db.has_automatic_freeze_report("99"))

    def test_generate_and_save_returns_none_without_active_sprint(self):
        jira_provider = MagicMock()
        jira_provider.fetch.return_value = {
            "items": [_make_task("FF-9", "A Fazer", "new")],
            "new_items": [],
            "errors": []
        }
        jira_provider.get_active_sprint.return_value = None
        github_provider = MagicMock()

        from src.core.sprint_freeze import generate_and_save
        report = generate_and_save(jira_provider, github_provider, self.db, production_branch="rc-prod")
        self.assertIsNone(report)

    def test_generate_and_save_returns_none_without_top_level_tasks(self):
        jira_provider = MagicMock()
        jira_provider.fetch.return_value = {
            "items": [_make_task("FF-9-SUB1", "A Fazer", "new", is_subtask=True)],
            "new_items": [],
            "errors": []
        }
        github_provider = MagicMock()

        from src.core.sprint_freeze import generate_and_save
        report = generate_and_save(jira_provider, github_provider, self.db, production_branch="rc-prod")
        self.assertIsNone(report)
        jira_provider.get_active_sprint.assert_not_called()
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

Run: `python3 -m unittest tests.test_sprint_freeze -k GenerateAndSave -v`
Expected: FAIL (`ImportError: cannot import name 'generate_and_save'`)

- [ ] **Step 3: Implementar em `src/core/sprint_freeze.py`**

No topo do arquivo, atualizar os imports:

```python
"""
Serviço de geração do Relatório de Sprint Freeze: cruza tarefas do Jira com
PRs de promoção no GitHub para identificar o que não chegou em produção.
"""
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional

from .database import DatabaseManager
from .models import JiraSprintInfo, JiraTaskItem, SprintFreezeReport, SprintFreezeTaskEntry
from .pdf_report import render_report_pdf
```

No final do arquivo, após `should_generate_automatic_report`, adicionar:

```python


def default_reports_dir() -> Path:
    """Diretório padrão de armazenamento dos PDFs, no mesmo padrão XDG do banco SQLite."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    base_dir = Path(xdg_data) / "dev-status-widget" if xdg_data else Path.home() / ".local" / "share" / "dev-status-widget"
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def generate_and_save(
    jira_provider,
    github_provider,
    db: DatabaseManager,
    production_branch: str,
    is_automatic: bool = False,
    reports_dir: Optional[Path] = None,
) -> Optional[SprintFreezeReport]:
    """
    Gera um relatório completo: busca as tarefas atuais do Jira, descobre a
    sprint ativa, cruza com o GitHub, renderiza o PDF e salva o registro no
    banco. Retorna None se não houver tarefas de nível superior na sprint ou
    nenhuma sprint ativa for encontrada.
    """
    jira_result = jira_provider.fetch()
    jira_tasks: List[JiraTaskItem] = jira_result.get("items", [])
    top_level_tasks = [t for t in jira_tasks if not t.is_subtask]
    if not top_level_tasks:
        return None

    sprint_info = jira_provider.get_active_sprint(top_level_tasks[0].key)
    if sprint_info is None:
        return None

    task_keys = [t.key for t in top_level_tasks]
    promotion_status, github_search_failed = github_provider.search_promotion_prs(task_keys, production_branch)

    report = build_report(
        top_level_tasks, sprint_info, promotion_status,
        is_automatic=is_automatic, github_search_failed=github_search_failed
    )

    target_dir = reports_dir or default_reports_dir()
    safe_sprint_name = "".join(c if c.isalnum() else "_" for c in report.sprint_name).strip("_") or report.sprint_id
    filename = f"{safe_sprint_name}_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = str(target_dir / filename)
    render_report_pdf(report, pdf_path)
    report.pdf_path = pdf_path

    report.id = db.save_freeze_report(report)
    return report
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python3 -m unittest tests.test_sprint_freeze -v`
Expected: PASS (todos os testes do arquivo, incluindo os das Tasks 5 e 7)

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

### Task 8: Widget `FreezeReportCard`

**Files:**
- Create: `src/ui/widgets/freeze_report_card.py`
- Modify: `tests/test_sprint_freeze.py`

**Interfaces:**
- Consumes: `SprintFreezeReport` (Task 1).
- Produces: `FreezeReportCard(report: SprintFreezeReport, parent=None)` — sinal `download_clicked = pyqtSignal(str)`; atributos públicos `download_btn`, `summary_label`.

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_sprint_freeze.py`:

```python
class TestFreezeReportCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_card_shows_summary_and_emits_download(self):
        from src.ui.widgets.freeze_report_card import FreezeReportCard
        from src.core.models import SprintFreezeReport

        report = SprintFreezeReport(
            id=1, sprint_id="10", sprint_name="Sprint 42",
            generated_at=datetime.now(timezone.utc), is_automatic=True,
            total_tasks=18, promoted_count=11, retained_count=7,
            pdf_path="/tmp/relatorio.pdf"
        )
        card = FreezeReportCard(report)

        captured = []
        card.download_clicked.connect(lambda path: captured.append(path))
        card.download_btn.click()

        self.assertEqual(captured, ["/tmp/relatorio.pdf"])
        self.assertIn("11 promovidas", card.summary_label.text())
        self.assertIn("7 retidas", card.summary_label.text())
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

Run: `python3 -m unittest tests.test_sprint_freeze -k FreezeReportCard -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.ui.widgets.freeze_report_card'`)

- [ ] **Step 3: Implementar `src/ui/widgets/freeze_report_card.py`**

```python
"""
Card visual para exibição de um relatório de Sprint Freeze já gerado.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.models import SprintFreezeReport


class FreezeReportCard(QFrame):
    download_clicked = pyqtSignal(str)

    def __init__(self, report: SprintFreezeReport, parent: QWidget = None):
        super().__init__(parent)
        self.report = report
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            FreezeReportCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                margin-bottom: 6px;
            }
            FreezeReportCard:hover {
                background-color: #1c2128;
                border-color: #444c56;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(12)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        date_str = self.report.generated_at.strftime("%d/%m/%Y %H:%M")
        origin = "🤖 Automático" if self.report.is_automatic else "🖱️ Manual"

        title_lbl = QLabel(f"🧊 {self.report.sprint_name} — {date_str} ({origin})")
        title_lbl.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: 600;")
        content_layout.addWidget(title_lbl)

        self.summary_label = QLabel(
            f"{self.report.promoted_count} promovidas / {self.report.retained_count} retidas "
            f"de {self.report.total_tasks} tarefas"
        )
        self.summary_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        content_layout.addWidget(self.summary_label)

        main_layout.addLayout(content_layout, stretch=1)

        self.download_btn = QPushButton("⬇️ Baixar PDF")
        self.download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.download_btn.setProperty("class", "actionButton")
        self.download_btn.clicked.connect(lambda: self.download_clicked.emit(self.report.pdf_path))
        main_layout.addWidget(self.download_btn, 0, Qt.AlignmentFlag.AlignVCenter)
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python3 -m unittest tests.test_sprint_freeze -k FreezeReportCard -v`
Expected: PASS

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

### Task 9: View `FreezeReportView`

**Files:**
- Create: `src/ui/views/freeze_report_view.py`
- Modify: `tests/test_sprint_freeze.py`

**Interfaces:**
- Consumes: `FreezeReportCard` (Task 8), `SprintFreezeReport` (Task 1).
- Produces: `FreezeReportView()` — sinais `generate_requested = pyqtSignal()`, `download_requested = pyqtSignal(str)`; métodos `set_reports(reports: List[SprintFreezeReport])`, `set_generating(generating: bool)`; atributos públicos `generate_btn`, `status_label`, `cards_layout`.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao final de `tests/test_sprint_freeze.py`:

```python
class TestFreezeReportView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_set_reports_renders_cards_and_status(self):
        from src.ui.views.freeze_report_view import FreezeReportView
        from src.core.models import SprintFreezeReport

        view = FreezeReportView()
        reports = [
            SprintFreezeReport(
                id=1, sprint_id="10", sprint_name="Sprint 42",
                generated_at=datetime.now(timezone.utc), is_automatic=False,
                total_tasks=18, promoted_count=11, retained_count=7,
                pdf_path="/tmp/r.pdf"
            )
        ]

        captured = []
        view.download_requested.connect(lambda path: captured.append(path))
        view.set_reports(reports)

        self.assertEqual(view.cards_layout.count(), 1)
        self.assertIn("11 promovidas", view.status_label.text())

    def test_generate_button_emits_signal(self):
        from src.ui.views.freeze_report_view import FreezeReportView

        view = FreezeReportView()
        captured = []
        view.generate_requested.connect(lambda: captured.append(True))
        view.generate_btn.click()
        self.assertEqual(captured, [True])

    def test_set_generating_disables_button(self):
        from src.ui.views.freeze_report_view import FreezeReportView

        view = FreezeReportView()
        view.set_generating(True)
        self.assertFalse(view.generate_btn.isEnabled())
        view.set_generating(False)
        self.assertTrue(view.generate_btn.isEnabled())
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

Run: `python3 -m unittest tests.test_sprint_freeze -k FreezeReportView -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.ui.views.freeze_report_view'`)

- [ ] **Step 3: Implementar `src/ui/views/freeze_report_view.py`**

```python
"""
Visualização da aba de Relatórios de Sprint Freeze.
"""
from typing import List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.models import SprintFreezeReport
from ..widgets.freeze_report_card import FreezeReportCard


class FreezeReportView(QWidget):
    generate_requested = pyqtSignal()
    download_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.reports: List[SprintFreezeReport] = []
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header_frame = QFrame()
        header_frame.setObjectName("filterBarFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        self.title_label = QLabel("🧊 Relatórios de Sprint Freeze")
        self.title_label.setStyleSheet("color: #cdd6f4; font-size: 13px; font-weight: 600;")
        header_layout.addWidget(self.title_label)

        self.status_label = QLabel("Nenhum relatório gerado ainda.")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        self.generate_btn = QPushButton("🧊 Gerar Relatório Agora")
        self.generate_btn.setProperty("class", "primaryButton")
        self.generate_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.generate_btn.clicked.connect(self.generate_requested.emit)
        header_layout.addWidget(self.generate_btn)

        root_layout.addWidget(header_frame)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(14, 14, 14, 14)
        self.cards_layout.setSpacing(6)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.empty_label = QLabel(
            "Nenhum relatório gerado ainda.\nClique em \"Gerar Relatório Agora\" para criar o primeiro."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #7d8590; font-size: 14px; padding: 40px; line-height: 1.5;")
        self.cards_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.container)
        root_layout.addWidget(self.scroll_area, stretch=1)

    def set_reports(self, reports: List[SprintFreezeReport]):
        self.reports = reports

        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not reports:
            self.empty_label = QLabel(
                "Nenhum relatório gerado ainda.\nClique em \"Gerar Relatório Agora\" para criar o primeiro."
            )
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet("color: #7d8590; font-size: 14px; padding: 40px; line-height: 1.5;")
            self.cards_layout.addWidget(self.empty_label)
            self.status_label.setText("Nenhum relatório gerado ainda.")
        else:
            for report in reports:
                card = FreezeReportCard(report, parent=self.container)
                card.download_clicked.connect(self.download_requested.emit)
                self.cards_layout.addWidget(card)
            last = reports[0]
            self.status_label.setText(
                f"Última geração: {last.generated_at.strftime('%d/%m/%Y %H:%M')} — "
                f"{last.promoted_count} promovidas / {last.retained_count} retidas"
            )

    def set_generating(self, generating: bool):
        self.generate_btn.setEnabled(not generating)
        self.generate_btn.setText("⏳ Gerando..." if generating else "🧊 Gerar Relatório Agora")
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python3 -m unittest tests.test_sprint_freeze -v`
Expected: PASS (todos os testes do arquivo)

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

### Task 10: Configurações — seção "🧊 Relatório de Freeze de Sprint"

**Files:**
- Modify: `src/ui/views/settings_view.py`
- Modify: `tests/test_widget.py`

**Interfaces:**
- Consumes: `AppConfig.freeze_reports_enabled`, `AppConfig.freeze_production_branch` (Task 1).
- Produces: `SettingsView.freeze_enabled_check` (QCheckBox), `SettingsView.freeze_branch_input` (QLineEdit) — expostos publicamente para o `MainWindow` e para testes.

- [ ] **Step 1: Escrever o teste que falha**

Adicionar em `tests/test_widget.py`:

```python
class TestSettingsView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_freeze_fields_roundtrip(self):
        from src.ui.views.settings_view import SettingsView

        config = AppConfig(freeze_reports_enabled=True, freeze_production_branch="rc-prod")
        view = SettingsView(config=config)

        self.assertTrue(view.freeze_enabled_check.isChecked())
        self.assertEqual(view.freeze_branch_input.text(), "rc-prod")

        view.freeze_enabled_check.setChecked(False)
        view.freeze_branch_input.setText("main")

        captured = {}
        view.settings_saved.connect(lambda cfg: captured.update(config=cfg))
        view._save()

        self.assertFalse(captured["config"].freeze_reports_enabled)
        self.assertEqual(captured["config"].freeze_production_branch, "main")
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

Run: `python3 -m unittest tests.test_widget -k TestSettingsView -v`
Expected: FAIL (`AttributeError: 'SettingsView' object has no attribute 'freeze_enabled_check'`)

- [ ] **Step 3: Implementar em `src/ui/views/settings_view.py`**

Logo após `layout.addWidget(jira_group)` (fim da seção 3, Integração com o Jira) e antes do comentário `# 4. Preferências Gerais`, adicionar:

```python

        # 3.5 Relatório de Sprint Freeze
        freeze_group = QGroupBox("🧊 Relatório de Freeze de Sprint")
        freeze_group.setStyleSheet("QGroupBox { font-weight: bold; color: #89b4fa; }")
        freeze_layout = QVBoxLayout(freeze_group)
        freeze_layout.setSpacing(10)

        self.freeze_enabled_check = QCheckBox("Habilitar aba e geração automática do relatório de Sprint Freeze")
        self.freeze_enabled_check.setStyleSheet("font-weight: 500;")
        freeze_layout.addWidget(self.freeze_enabled_check)

        freeze_desc = QLabel(
            "Requer a integração com o Jira habilitada acima. Gera às segundas-feiras\n"
            "(quando a sprint ativa já passou da data de término) um relatório das\n"
            "tarefas que não chegaram na branch de produção configurada abaixo."
        )
        freeze_desc.setWordWrap(True)
        freeze_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        freeze_layout.addWidget(freeze_desc)

        freeze_form = QGridLayout()
        freeze_form.setSpacing(8)
        freeze_form.addWidget(QLabel("Branch de Produção:"), 0, 0)
        self.freeze_branch_input = QLineEdit()
        self.freeze_branch_input.setPlaceholderText("rc-prod")
        freeze_form.addWidget(self.freeze_branch_input, 0, 1)
        freeze_layout.addLayout(freeze_form)

        layout.addWidget(freeze_group)
```

Dentro de `load_config()`, logo após `self.jira_jql_input.setText(config.jira_jql)`, adicionar:

```python

        # Sprint Freeze
        self.freeze_enabled_check.setChecked(config.freeze_reports_enabled)
        self.freeze_branch_input.setText(config.freeze_production_branch)
```

Dentro de `_save()`, no construtor de `AppConfig(...)`, logo após `jira_jql=self.jira_jql_input.text().strip() or "sprint in openSprints() AND (assignee = currentUser() OR assignee is EMPTY) AND issuetype not in subtaskIssueTypes() ORDER BY updated DESC",`, adicionar:

```python
            freeze_reports_enabled=self.freeze_enabled_check.isChecked(),
            freeze_production_branch=self.freeze_branch_input.text().strip() or "rc-prod",
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python3 -m unittest tests.test_widget -k TestSettingsView -v`
Expected: PASS

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

### Task 11: MainWindow — aba "🧊 Freeze" e geração manual

**Files:**
- Modify: `src/ui/main_window.py`

**Interfaces:**
- Consumes: `FreezeReportView` (Task 9), `generate_and_save()` (Task 7), `DatabaseManager.get_freeze_reports()` (Task 2), `SettingsView.freeze_enabled_check`/`freeze_branch_input` (Task 10).
- Produces: `MainWindow.tab_freeze`, `MainWindow.freeze_report_view`, `MainWindow._on_generate_freeze_report()`, `MainWindow._on_freeze_report_generated(report, error)`, `MainWindow._on_download_freeze_report(pdf_path)`, `MainWindow.is_generating_freeze_report: bool`.

Esta tarefa é de integração de UI (thread + Qt), sem teste automatizado novo — segue o mesmo padrão já usado no projeto para `FetchWorker`/`CheckUpdateWorker`, que também não têm testes unitários dedicados (só verificação manual rodando o app). A verificação acontece no Passo 6.

- [ ] **Step 1: Atualizar imports em `src/ui/main_window.py`**

No topo do arquivo, adicionar:

```python
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core.config import ConfigManager
from ..core.database import DatabaseManager
from ..core.models import AppConfig
from ..core.notifier import DesktopNotifier
from ..core.sprint_freeze import generate_and_save
from ..core.updater import GitUpdater, UpdateInfo
from ..providers.github_provider import GitHubProvider
from ..providers.jira_provider import JiraProvider
from .dock_badge import DockBadgeManager
from .tray import SystemTrayManager
from .views.freeze_report_view import FreezeReportView
from .views.jira_view import JiraView
from .views.notifications_view import NotificationsView
from .views.prs_view import PullRequestsView
from .views.settings_view import SettingsView
from .widgets.tab_button import NavTabButton
from .widgets.update_banner import UpdateBannerWidget
```

(a única linha nova de fato é `from ..core.sprint_freeze import ...`, `from .views.freeze_report_view import FreezeReportView`, `import shutil` e `from pathlib import Path` e `QFileDialog` no import do PyQt6.QtWidgets — as demais já existem e devem ser mantidas como estão.)

- [ ] **Step 2: Adicionar o `FreezeReportWorker`**

Logo após a classe `CheckUpdateWorker` (antes de `class MainWindow`), adicionar:

```python
class FreezeReportWorker(QObject):
    # Emite (report: Optional[SprintFreezeReport], error: Optional[str]).
    # `error` só é preenchido quando algo realmente falhou (ex: PDF não
    # renderizou); report=None com error=None significa "sem sprint ativa
    # ou sem tarefas", um caso normal e silencioso.
    finished = pyqtSignal(object, object)

    def __init__(self, jira_provider, github_provider, db, production_branch: str, is_automatic: bool = False):
        super().__init__()
        self.jira_provider = jira_provider
        self.github_provider = github_provider
        self.db = db
        self.production_branch = production_branch
        self.is_automatic = is_automatic

    def run(self):
        try:
            report = generate_and_save(
                self.jira_provider,
                self.github_provider,
                self.db,
                self.production_branch,
                is_automatic=self.is_automatic
            )
            self.finished.emit(report, None)
        except Exception as e:
            print(f"[SprintFreeze] Erro ao gerar relatório: {e}")
            self.finished.emit(None, str(e))
```

- [ ] **Step 3: Inicializar estado no `MainWindow.__init__`**

Logo após `self.worker: FetchWorker = None` / `self.is_fetching = False`, adicionar:

```python

        # Relatório de Sprint Freeze
        self.is_generating_freeze_report = False
        self.freeze_thread: QThread = None
        self.freeze_worker: FreezeReportWorker = None
        self._last_jira_task_keys: list = []
```

- [ ] **Step 4: Adicionar a aba, a view e o carregamento inicial em `_init_ui`**

Logo após o bloco da Aba 3 (Configurações) — após `tab_layout.addWidget(self.tab_settings)` — adicionar a nova aba:

```python

        # Aba 4: Relatórios de Sprint Freeze
        self.tab_freeze = NavTabButton("🧊 Freeze", count=0)
        self.tab_freeze.set_active(False)
        self.tab_freeze.clicked.connect(lambda: self._switch_tab(4))
        self.tab_freeze.setVisible(self.config.freeze_reports_enabled and self.config.jira_enabled)
        tab_layout.addWidget(self.tab_freeze)
```

Logo após `self.stack.addWidget(self.settings_view)` (fim da View 3), adicionar:

```python

        # View 4: Relatórios de Sprint Freeze
        self.freeze_report_view = FreezeReportView()
        self.freeze_report_view.generate_requested.connect(self._on_generate_freeze_report)
        self.freeze_report_view.download_requested.connect(self._on_download_freeze_report)
        self.stack.addWidget(self.freeze_report_view)
```

Atualizar `_switch_tab` para reconhecer a 5ª aba:

```python
    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.tab_prs.set_active(index == 0)
        self.tab_jira.set_active(index == 1)
        self.tab_notifications.set_active(index == 2)
        self.tab_settings.set_active(index == 3)
        self.tab_freeze.set_active(index == 4)
```

Em `_load_from_cache`, logo após o bloco `self._reload_notifications()`, adicionar:

```python
            self.freeze_report_view.set_reports(self.db.get_freeze_reports())
```

- [ ] **Step 5: Adicionar os handlers de geração manual e download**

No final da classe `MainWindow` (após `_on_manual_update_check_completed` ou `show_update_details`, antes de `prompt_and_perform_update`), adicionar:

```python

    def _on_generate_freeze_report(self):
        if self.is_generating_freeze_report:
            return
        if not self.config.jira_enabled:
            self.status_bar.showMessage(
                "Habilite a integração com o Jira nas Configurações antes de gerar o relatório de freeze.", 5000
            )
            return

        self.is_generating_freeze_report = True
        self.freeze_report_view.set_generating(True)
        self.status_bar.showMessage("Gerando relatório de Sprint Freeze...")
        self._start_freeze_generation(is_automatic=False)

    def _start_freeze_generation(self, is_automatic: bool):
        self.freeze_thread = QThread()
        self.freeze_worker = FreezeReportWorker(
            self.jira_provider,
            self.github_provider,
            self.db,
            self.config.freeze_production_branch,
            is_automatic=is_automatic
        )
        self.freeze_worker.moveToThread(self.freeze_thread)

        self.freeze_thread.started.connect(self.freeze_worker.run)
        self.freeze_worker.finished.connect(self._on_freeze_report_generated)
        self.freeze_worker.finished.connect(self.freeze_thread.quit)
        self.freeze_worker.finished.connect(self.freeze_worker.deleteLater)
        self.freeze_thread.finished.connect(self.freeze_thread.deleteLater)

        self.freeze_thread.start()

    def _on_freeze_report_generated(self, report, error):
        self.is_generating_freeze_report = False
        self.freeze_report_view.set_generating(False)

        if error:
            QMessageBox.critical(
                self, "Erro ao Gerar Relatório",
                f"Ocorreu um erro ao gerar o relatório de Sprint Freeze:\n\n{error}\n\n"
                "Se o erro mencionar bibliotecas do WeasyPrint, rode o install.sh novamente."
            )
            self.status_bar.showMessage("Erro ao gerar relatório de Sprint Freeze.", 5000)
            return

        if report is None:
            self.status_bar.showMessage(
                "Não foi possível gerar o relatório: nenhuma sprint ativa encontrada.", 5000
            )
            return

        self.freeze_report_view.set_reports(self.db.get_freeze_reports())
        self.status_bar.showMessage(
            f"Relatório de Freeze gerado: {report.promoted_count} promovidas / {report.retained_count} retidas.",
            5000
        )

    def _on_download_freeze_report(self, pdf_path: str):
        if not pdf_path or not os.path.exists(pdf_path):
            QMessageBox.warning(
                self, "Arquivo não encontrado",
                "O arquivo PDF deste relatório não foi encontrado no disco."
            )
            return

        suggested_name = os.path.basename(pdf_path)
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório de Freeze", suggested_name, "PDF (*.pdf)"
        )
        if dest_path:
            try:
                shutil.copyfile(pdf_path, dest_path)
                self.status_bar.showMessage(f"Relatório salvo em {dest_path}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao salvar", f"Não foi possível salvar o arquivo:\n{e}")
```

- [ ] **Step 6: Wiring de configurações e tarefas Jira recém-buscadas**

Em `_on_settings_saved`, logo após `self.tab_jira.setVisible(new_config.jira_enabled)`, adicionar:

```python
        self.tab_freeze.setVisible(new_config.freeze_reports_enabled and new_config.jira_enabled)
```

Em `_on_fetch_completed`, logo após a linha `self.jira_view.update_tasks(jira_items, current_user_name=jira_user)`, adicionar:

```python
        self._last_jira_task_keys = [t.key for t in jira_items if not t.is_subtask]
```

- [ ] **Step 7: Verificação manual (sem teste automatizado — mesmo padrão de `FetchWorker`)**

Run: `python3 main.py --demo`

Confirmar manualmente:
1. A aba "🧊 Freeze" só aparece se `freeze_reports_enabled: true` e `jira_enabled: true` estiverem no `config.yaml` (ajustar o arquivo local de teste conforme necessário).
2. Clicar em "🧊 Gerar Relatório Agora" gera um PDF em `~/.local/share/dev-status-widget/reports/` e o item aparece na lista.
3. Clicar em "⬇️ Baixar PDF" abre o diálogo "Salvar como..." e copia o arquivo.

- [ ] **Step 8: Revisar o diff (sem commit automático)**

---

### Task 12: MainWindow — checagem automática de segunda-feira

**Files:**
- Modify: `src/ui/main_window.py`

**Interfaces:**
- Consumes: `should_generate_automatic_report()` (Task 5), `JiraProvider.get_active_sprint()` (Task 3), `DatabaseManager.has_automatic_freeze_report()` (Task 2), `MainWindow._start_freeze_generation()` (Task 11).
- Produces: `MainWindow.freeze_check_timer`, `MainWindow._check_automatic_freeze_report()`.

Assim como a Task 11, esta é uma tarefa de integração Qt/timer sem teste automatizado dedicado — a lógica de decisão pura já está coberta pelos testes de `should_generate_automatic_report` (Task 5). A verificação é manual (Passo 3).

- [ ] **Step 1: Criar e iniciar o timer no `__init__`**

Logo após o bloco `self._start_timer()` (chamada existente no `__init__`), adicionar:

```python

        # Timer de checagem da automação de Sprint Freeze (a cada hora)
        self.freeze_check_timer = QTimer(self)
        self.freeze_check_timer.timeout.connect(self._check_automatic_freeze_report)
        self.freeze_check_timer.start(60 * 60 * 1000)
```

- [ ] **Step 2: Implementar `_check_automatic_freeze_report`**

Adicionar logo após `_on_download_freeze_report` (Task 11):

```python

    def _check_automatic_freeze_report(self):
        if not (self.config.freeze_reports_enabled and self.config.jira_enabled):
            return
        if self.is_generating_freeze_report:
            return
        if not self._last_jira_task_keys:
            return

        from datetime import date
        from ..core.sprint_freeze import should_generate_automatic_report

        sprint_info = self.jira_provider.get_active_sprint(self._last_jira_task_keys[0])
        if sprint_info is None:
            return

        already_has_automatic = self.db.has_automatic_freeze_report(str(sprint_info.id))
        if should_generate_automatic_report(date.today(), sprint_info.end_date, already_has_automatic):
            self.is_generating_freeze_report = True
            self.freeze_report_view.set_generating(True)
            self.status_bar.showMessage(
                "Gerando relatório automático de Sprint Freeze (segunda-feira de virada)...", 5000
            )
            self._start_freeze_generation(is_automatic=True)
```

- [ ] **Step 3: Verificação manual**

Não é possível testar a espera de 1 hora de forma automatizada sem acoplar o teste ao relógio real. Verificar manualmente chamando o método direto no console de depuração (ex: um teste manual ad-hoc via `python3 -c` instanciando `MainWindow` com providers mockados e chamando `_check_automatic_freeze_report()`), ou aceitar a cobertura indireta via `should_generate_automatic_report` (Task 5) e `generate_and_save` (Task 7), que já cobrem toda a lógica de decisão e geração — o método do `MainWindow` apenas os conecta ao timer e ao estado da UI.

- [ ] **Step 4: Rodar a suíte de testes completa**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (todos os testes do projeto, incluindo os novos das Tasks 1–10)

- [ ] **Step 5: Revisar o diff (sem commit automático)**

---

## Manual Verification Checklist

Após todas as tasks implementadas, com o app rodando (`python3 main.py`) e `jira_enabled: true` + `freeze_reports_enabled: true` + `freeze_production_branch` configurados com credenciais reais do Jira/GitHub:

1. A aba "🧊 Freeze" aparece na barra de navegação.
2. "🧊 Gerar Relatório Agora" gera um PDF real com as tarefas retidas da sprint ativa e o item some da lista de "promovidas" quando há PR mesclada para a branch configurada.
3. O PDF gerado abre corretamente em um leitor de PDF e mostra o resumo + tabela de tarefas retidas.
4. "⬇️ Baixar PDF" salva uma cópia no local escolhido pelo usuário.
5. Alterar `freeze_reports_enabled` para `false` nas Configurações esconde a aba.
6. Rodar `python3 -m unittest discover -s tests -v` com todos os testes passando.

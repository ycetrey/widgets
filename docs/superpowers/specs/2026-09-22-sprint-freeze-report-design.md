# Relatório de Sprint Freeze — Design

Data: 2026-09-22
Status: Aprovado pelo usuário em brainstorming (aguardando plano de implementação)

## Contexto e objetivo

O Dev Status Widget (app desktop PyQt6) já monitora PRs do GitHub e tarefas do
Jira. O usuário quer um botão para gerar um relatório de "sprint freeze":
identificar, na segunda-feira em que a sprint vira, quais tarefas da sprint
que está terminando **não chegaram em produção**, com um PDF baixável e um
histórico de relatórios gerados em uma nova aba.

Um exemplo de GitHub Action (Jira API + GitHub API, para os repositórios
`Fiscalmax/api-monorepo`, `front-client`, `front-consultant`) foi fornecido
como referência de conteúdo/lógica do relatório — **não é implementado neste
repositório**; serve apenas de inspiração para a lógica de cruzamento e o
layout do relatório. A Action em si é um projeto separado, futuro, para
redundância (envio por e-mail).

## Decisões tomadas (brainstorming)

1. **Critério de "chegou em produção"**: cruza Jira (status) + GitHub (PR de
   promoção mesclada) — não usa só um dos dois.
2. **Automação de segunda-feira**: roda dentro do próprio widget (enquanto
   ele estiver aberto/em background), além do botão manual.
3. **Datas da sprint**: vêm da Jira Agile API (`startDate`/`endDate` reais),
   não de cálculo local.
4. **Identificação da PR de promoção**: título/branch contém a chave da
   tarefa **E** a branch de destino é uma branch de produção configurável
   (padrão `rc-prod`).
5. **Repositórios verificados**: reaproveita a lista já configurada na aba
   PRs (sem campo novo).
6. **Board do Jira**: descoberto automaticamente (via prefixo da chave das
   tarefas + Agile API), sem exigir o usuário informar o board ID.
7. **Geração do PDF**: HTML estilizado (reaproveitando o layout do exemplo
   colado) → PDF via WeasyPrint (não ReportLab).

## Arquitetura e componentes novos

Segue o padrão já existente no projeto (Provider → View → Database). Não
introduz um scheduler externo (ex: APScheduler); reaproveita o mecanismo de
`QTimer` que a `MainWindow` já usa para o refresh automático.

- `src/core/sprint_freeze.py` — `SprintFreezeService`: orquestra o
  cruzamento Jira+GitHub e monta o objeto de relatório.
- `src/core/pdf_report.py` — renderiza o HTML do relatório e converte para
  PDF via WeasyPrint.
- `src/providers/jira_provider.py` — novo método `get_active_sprint()`:
  descobre o board do projeto (prefixo da chave das tarefas já buscadas,
  ex: `FF-1234` → projeto `FF`) via `/rest/agile/1.0/board`, depois busca o
  sprint ativo via `/rest/agile/1.0/board/{id}/sprint?state=active`
  (retorna `id`, `name`, `startDate`, `endDate`).
- `src/providers/github_provider.py` — novo método
  `search_promotion_prs(task_keys, base_branch)`: usa a GitHub Search Issues
  API (`is:pr base:{branch}` + chaves da sprint em lotes com `OR`, um lote
  por repositório configurado), classificando cada PR retornada como
  mesclada ou aberta via o campo `pull_request.merged_at`.
- `src/core/database.py` — nova tabela `freeze_reports` (histórico dos
  relatórios gerados).
- `src/ui/views/freeze_report_view.py` +
  `src/ui/widgets/freeze_report_card.py` — nova aba "🧊 Freeze".
- `src/core/models.py` — novos dataclasses `SprintFreezeTaskEntry` e
  `SprintFreezeReport`.

## Lógica de cruzamento (critério "chegou em produção")

Para cada tarefa (não-subtarefa) da sprint ativa:

1. Busca no GitHub qualquer PR (aberta ou fechada) cujo título/branch
   contenha a chave da tarefa **e** cuja branch de destino seja a
   `freeze_production_branch` configurada (padrão `rc-prod`).
2. PR **mesclada** encontrada → tarefa "Promovida" (conta só no resumo, não
   aparece na lista detalhada do relatório).
3. PR **aberta** (não mesclada) encontrada → tarefa "Retida", diagnóstico =
   `⚠️ PR aberta aguardando merge` com link da PR.
4. **Nenhuma PR** encontrada → tarefa "Retida", diagnóstico = status atual
   da tarefa no Jira (com emoji por categoria: `new`→🔨, `indeterminate`→🧪,
   mostrando o nome literal do status).

Simplificação deliberada: não infere "em Dev" vs "em QA" a partir de nomes
específicos de subtarefas (ex: "Dev: Merge na rc-prod") como no exemplo
colado — isso é frágil (depende de nomenclatura exata) e foge do escopo
mínimo necessário. Usa-se diretamente o status do Jira, que é a fonte
confiável disponível. Aprovado pelo usuário.

## Gatilho de geração automática (segunda-feira)

- A cada hora (timer independente do refresh de PRs/Jira), verifica:
  `hoje é segunda-feira` **e** `sprint ativa tem endDate <= agora`.
- Antes de gerar, checa no banco se já existe um relatório **automático**
  para aquele `sprint_id` (evita gerar de novo a cada hora na mesma
  segunda). O botão manual sempre pode gerar de novo (útil para checar
  progresso no meio da semana), sem essa trava.
- Geração automática e manual não rodam simultaneamente (trava tipo
  `is_fetching`, adaptada para essa operação).

## UI — nova aba "🧊 Freeze"

Visível apenas se `freeze_reports_enabled=True` (que por sua vez exige
`jira_enabled=True`).

- **Topo**: botão `[ 🧊 Gerar Relatório Agora ]` + status (última geração,
  sprint atual detectada) + resumo do último relatório (ex: "11 promovidas
  / 7 retidas").
- **Lista abaixo** (mais recente primeiro), linha a linha: data de geração,
  nome da sprint, resumo de contagem, botão `[ ⬇️ Baixar PDF ]`.
- **Download**: o PDF já fica salvo localmente em
  `~/.local/share/dev-status-widget/reports/`; o botão abre um diálogo
  "Salvar como..." (`QFileDialog`) para copiar o arquivo para onde o
  usuário quiser.

## Configurações novas (aba ⚙️)

Nova seção "🧊 Relatório de Freeze de Sprint":
- Toggle `freeze_reports_enabled: bool = False` (padrão desligado).
- Campo texto `freeze_production_branch: str = "rc-prod"`.

## Modelo de dados

```python
@dataclass
class SprintFreezeTaskEntry:
    key: str
    summary: str
    assignee: str
    jira_status: str
    html_url: str
    diagnosis: str            # ex: "🔨 A Fazer", "🧪 Em Progresso", "⚠️ PR aberta aguardando merge"
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

Tabela `freeze_reports` (SQLite, mesmo padrão de `database.py`):

```sql
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
```

Sem `UNIQUE(sprint_id)` — o botão manual pode gerar múltiplos relatórios
para a mesma sprint; a idempotência da geração automática é feita via
consulta (`WHERE sprint_id = ? AND is_automatic = 1`), não por constraint.

## Tratamento de erros

- Sprint ativa não encontrada / API Agile do Jira inacessível → geração
  automática é pulada silenciosamente (log interno); geração manual mostra
  mensagem clara na status bar/diálogo.
- GitHub Search retorna erro (rate limit/token inválido) → não aborta o
  relatório inteiro; marca a tarefa como `❔ Não foi possível verificar PR`
  e segue.
- Falha ao renderizar PDF (ex: libs do WeasyPrint ausentes) →
  `QMessageBox` de erro orientando rodar `install.sh` novamente; nenhum
  registro é salvo no banco.

## Dependências novas

- `weasyprint` (`requirements.txt`).
- Libs de sistema no `install.sh`: `libpango-1.0-0`, `libpangocairo-1.0-0`,
  `libgdk-pixbuf2.0-0`, `libcairo2`.

## Testes

Seguindo o padrão existente (`unittest` + `unittest.mock.patch` em
`requests.get/post`):

- `tests/test_sprint_freeze.py`: mocka Jira Agile API (sprint ativa) e
  GitHub Search API; cobre os 3 casos de diagnóstico (promovida / PR aberta
  / sem PR) e o gatilho de segunda-feira (`endDate` passado +
  `weekday()==0`).
- `tests/test_pdf_report.py`: gera um PDF a partir de um relatório fake e
  valida que o arquivo existe e começa com `%PDF`.
- `tests/test_database.py`: novos casos para `save_freeze_report` /
  `get_freeze_reports` / checagem de relatório automático já existente por
  sprint.

## Fora de escopo (este design)

- A GitHub Action externa (redundância por e-mail) mencionada pelo usuário
  — projeto separado, fora deste repositório.
- Inferência fina de gargalo por nome de subtarefa (Dev/QA) — usa status
  literal do Jira.

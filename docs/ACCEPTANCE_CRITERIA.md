# Critérios de aceite — tictactoe-api

Cada critério é objetivo e tem um comando exato. "Passa" = saída/código de retorno indicados.
Contratos referenciados (API, erros, portas, IA): `docs/REFACTOR_PLAN.md` seção 5.

## Preparação (uma vez por sessão)
Executar em **Git Bash**, com o repo mapeado numa letra curta (ver plano, seção 0.2):

```bash
cmd //c subst T: "C:\\Users\\vinio\\AppData\\Local\\Claude-Data\\claude_pzs8sxrjxfjjc\\scratch-workspaces\\ea839efe-b7a7-4785-92ad-0746174c9493\\58e189da-21c7-46fb-a813-66ec973ddf1f\\scratch-2026-11-23-e6aca0\\tictactoe-api"
cd /t/
export PYTHONDONTWRITEBYTECODE=1
PY=C:/v/ttt/Scripts/python          # venv curto fora do repo
```
(PowerShell equivalente: `subst T: "<caminho>"; Set-Location T:\`.) Ao final: `cmd //c subst T: //D`.

**Linha de base dos testes de aceite**: commit `BASELINE_PENDING` (ver AC-33).

---

## A. Higiene, renomeação e reprodutibilidade

| ID | Critério | Comando | Passa quando |
|---|---|---|---|
| AC-01 | `.env` não é versionado | `git ls-files .env` | saída vazia |
| AC-02 | `.env` é ignorado | `git check-ignore .env` | imprime `.env` (rc 0) |
| AC-03 | `.env.example` versionado com `DB_CONNECTION_STRING=` e `ML_MODEL_PATH=`, sem caminho absoluto | bloco AC-03 abaixo | 1 linha do ls-files + 2 linhas do grep |
| AC-04 | Nenhum artefato gerado versionado | `git ls-files '*.pth' '*.db' '*.sqlite' '*.sqlite3' '*.pyc'` | saída vazia |
| AC-05 | Nome antigo (`tictactoe_python_api`, `tictactoe_api`, "Tic Tac Toe Python API") ausente fora de `docs/` e `tests/acceptance/` | bloco AC-05 abaixo | saída vazia (rc 1) |
| AC-06 | Nenhum caminho absoluto de máquina (`X:\Users\...`, `/home/...`, `/Users/...`) fora de `docs/` e `tests/acceptance/` | bloco AC-06 abaixo | saída vazia (rc 1) |
| AC-07 | Metadados com o novo nome | `$PY -c "import tomllib;d=tomllib.load(open('pyproject.toml','rb'));print(d['project']['name'])"` | imprime `tictactoe-api` |
| AC-08 | README: 1ª linha `# tictactoe-api`; cita `.env.example`, `requirements-dev.txt`, `pytest`, `/api/health`, `/api/ai-train`; sem "Copiar código" | `head -1 README.md; $PY -m pytest tests/acceptance/test_repo_hygiene.py -k readme -q` | `# tictactoe-api` e `1 passed` |
| AC-09 | Dependências instalam do zero no Python 3.13 (Windows); runtime sem pytest/torchvision/torchaudio | `rm -rf C:/v/ttc && python -m venv C:/v/ttc && C:/v/ttc/Scripts/python -m pip install -q -r requirements.txt -r requirements-dev.txt && $PY -m pytest tests/acceptance/test_repo_hygiene.py -k requirements -q` | rc 0 e `1 passed` |

Comandos que contêm `|` (fora da tabela, para copiar sem escapes):

```bash
# AC-03
git ls-files .env.example && grep -E '^(DB_CONNECTION_STRING|ML_MODEL_PATH)=' .env.example
# AC-05
git grep -n -i -E 'tictactoe_python_api|tictactoe_api|tic tac toe python api' -- . ':!docs' ':!tests/acceptance'
# AC-06
git grep -n -E '[A-Za-z]:[\\/]+Users[\\/]+|/home/[A-Za-z]|/Users/[A-Za-z]' -- . ':!docs' ':!tests/acceptance'
```

## B. Arquitetura (testes estáticos em `tests/acceptance/test_architecture.py`)

| ID | Critério | Comando | Passa quando |
|---|---|---|---|
| AC-10 | `app/domain` não importa `app.application`, `app.infra`, `app.interface`, `app.container` nem flask/werkzeug/sqlalchemy/torch/numpy/dotenv | `$PY -m pytest tests/acceptance/test_architecture.py -k domain_depends -q` | `1 passed` |
| AC-11 | `app/application` só depende do domínio | `... -k application_depends -q` | `1 passed` |
| AC-12 | `app/interface` não importa `app.infra`/sqlalchemy/torch/dotenv; existe `app.container.build_container` | `... -k "interface_does_not or composition_root" -q` | `2 passed` |
| AC-13 | `app/infra` não importa interface/flask; torch só em `infra/ai`, sqlalchemy só em `infra/db`, flask só em `interface` | `... -k "infra_does_not or confined" -q` | `4 passed` |
| AC-14 | Adaptadores não leem configuração (sem `app.infra.settings`, `getenv`, `os.environ` em `infra/ai` e `infra/db/repositories`); "pth" não aparece em domain/application | `... -k "configuration or leak" -q` | `2 passed` |
| AC-15 | Todo adaptador em `app.infra` que implementa uma porta abstrata tem os mesmos nomes de parâmetros; ≥ 4 adaptadores | `... -k signatures -q` | `1 passed` |
| AC-16 | Adaptadores sem estado de classe (`cls.x = ...`, `setattr(cls, ...)`) | `... -k instance_based -q` | `1 passed` |
| AC-17 | `app.domain.exceptions.DomainError` com ≥ 4 subclasses; nenhum `except Exception`/`except:` sem `raise` em `app/` | `... -k "domain_errors or broad" -q` | `2 passed` |

(`...` = `$PY -m pytest tests/acceptance/test_architecture.py`.)

## C. Suíte do projeto

| ID | Critério | Comando | Passa quando |
|---|---|---|---|
| AC-18 | Suíte inteira passa em venv limpo, sem `SyntaxWarning` | `C:/v/ttc/Scripts/python -m pytest -q && C:/v/ttc/Scripts/python -W error::SyntaxWarning -m compileall -q -f app` | `N passed`, 0 failed/0 errors; compileall rc 0 |
| AC-19 | Testes antigos substituídos por testes reais e rasos | `git ls-files tests/application_tests tests/infrastructure_tests; $PY -m pytest tests --ignore=tests/acceptance -q` | ls-files vazio; ≥ 5 testes coletados, todos `passed` |

## D. Funcionalidade (HTTP via `app.test_client()`, sem rede e sem arquivos do autor)

| ID | Critério | Comando | Passa quando |
|---|---|---|---|
| AC-20 | `GET /api/health` → 200 `{"status":"ok","name":"tictactoe-api"}` | `$PY -m pytest tests/acceptance/test_game_flow.py -k health -q` | `1 passed` |
| AC-21 | Registrar → 201 com estatísticas 0; `GET /api/players/<id>` devolve o mesmo | `... test_game_flow.py -k register -q` | `1 passed` |
| AC-22 | `start` → 201, tabuleiro vazio, `in_progress`, `winner` 0, `movements` `[]` | `... -k start_returns -q` | `1 passed` |
| AC-23 | `move` atualiza tabuleiro e histórico | `... -k move_updates -q` | `1 passed` |
| AC-24 | Vitória detectada nas 8 linhas (3 linhas, 3 colunas, 2 diagonais) | `... -k every_line -q` | `8 passed` |
| AC-25 | Fluxo completo: vitória, derrota e empate na mesma conta; estatísticas 1/1/1; partida não termina antes da hora | `... -k "full_flow or not_finished" -q` | `2 passed` |
| AC-26 | Regras/erros B01–B13 (vitória na última casa, índices, marca, turno, casa ocupada, partida encerrada, jogador inexistente, partida duplicada, nickname, validação, 404s) | `$PY -m pytest tests/acceptance/test_regressions.py -k "b01 or b02 or b03 or b04 or b05 or b06 or b07 or b08 or b09 or b10 or b11 or b12 or b13" -q` | `25 passed` |
| AC-27 | Treinar com partidas jogadas e pedir jogada: sugestão é casa vazia, `position == row*3+column`, e é jogável como O | `$PY -m pytest tests/acceptance/test_ai_flow.py -k legal_move -q` | `1 passed` |
| AC-28 | IA B14–B20 (player-id, modelo ausente, vitória de O no treino, caminho do modelo, `amount`, sem dados, dataset) | `$PY -m pytest tests/acceptance/test_regressions.py -k "b14 or b15 or b16 or b17 or b18 or b19 or b20" -q` | `13 passed` |
| AC-29 | `ai-move` é somente leitura; partida encerrada → 409 `game_finished`; sem partidas → 404 `game_not_found` | `$PY -m pytest tests/acceptance/test_ai_flow.py -k "read_only or finished or without_games" -q` | `3 passed` |

## E. Entrega

| ID | Critério | Comando | Passa quando |
|---|---|---|---|
| AC-30 | Workflow de CI roda pytest no 3.13 com torch CPU | `ls .github/workflows/*.yml && $PY -m pytest tests/acceptance/test_repo_hygiene.py -k ci_workflow -q` | arquivo listado e `1 passed` |
| AC-31 | `main.py` sem `debug=True`; `create_app({"TESTING": True})` sobe sem `.env` | `$PY -m pytest tests/acceptance/test_repo_hygiene.py -k "debugger or dotenv_or_author" -q` | `2 passed` |
| AC-32 | Servidor real sobe (`python main.py` em dir temporário, `PORT` livre) e cumpre fluxo completo por HTTP (health, registrar, start, 5 jogadas até vitória, treinar, ai-move, estatísticas) | `$PY tests/acceptance/smoke_server.py` | imprime `SMOKE OK`, rc 0 |
| AC-33 | `tests/acceptance/` idêntico à linha de base | `git diff --exit-code BASELINE_PENDING -- tests/acceptance && test -z "$(git status --porcelain -- tests/acceptance)"` | rc 0 (sem diff, sem arquivos novos/não rastreados) |
| AC-34 | Suíte de aceite inteira | `$PY -m pytest tests/acceptance -q` | `81 passed` |
| AC-35 | Branch correta, nada enviado | `git rev-parse --abbrev-ref HEAD` | `refactor/tictactoe-api`; nenhum `git push` executado na implementação |

---

## Estado na linha de base (código atual, antes da implementação)
`$PY -m pytest tests/acceptance -q` → **75 não passam (20 failed + 55 errors), 6 passed**.
- Os 55 *errors* são todos `TypeError: create_app() takes 0 positional arguments but 1 was given` (fixture estrito). Com um shim de diagnóstico fora do repo (que injeta as variáveis de ambiente e cria as tabelas), os testes HTTP falham cada um pelo seu bug (ex.: B01 `assert 0 == 1`, B02 `assert 200 == 400`, B06 `assert 200 == 409`, B16 `Target -1 is out of bounds.`); apenas os 8 de AC-24 e o "partida não termina antes da hora" passam — a detecção de linhas atual está correta.
- Os 6 que já passam são guardas de arquitetura que o código atual respeita (domínio e aplicação limpos, infra sem interface, frameworks confinados). Ficam para impedir regressão durante a refatoração.
- `$PY tests/acceptance/smoke_server.py` → falha: servidor sai com `ArgumentError: Expected string or URL object, got None` (sem `.env` não há default).

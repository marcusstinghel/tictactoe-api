# Plano de refatoração: tictactoe-api

Branch: `refactor/tictactoe-api`. Público: quem vai implementar.
Critérios e comandos de verificação: `docs/ACCEPTANCE_CRITERIA.md`. Testes de aceite: `tests/acceptance/`.
**Não altere nada em `tests/acceptance/`** (AC-33). Se um teste parecer errado, pare e reporte; não o "conserte".

Estado atual verificado (2026-11-23, Python 3.13.7, Windows):
- A suíte existente (7 testes em 11 arquivos `.py`) **falha inteira**: os testes leem `C:/Users/vinio/Projects/tictactoe_api/.env`, dependem de linhas que já existem num banco local (player 1, partida em andamento) e não têm nenhum `assert`. Dois arquivos nem chegam a ser importados quando o repositório está num caminho longo (ver 0.2).
- `pip install -r requirements.txt` **não funciona** no Python 3.13 do Windows: não existe wheel de `torch==2.5.1` para cp313/win_amd64 (`No matching distribution found`).
- Com isso resolvido: rodar `python main.py` num diretório sem `.env` quebra com `ArgumentError: Expected string or URL object, got None`.
- Detecção de vitória nas 8 linhas: **correta** hoje (os testes parametrizados passam usando um shim de diagnóstico). O empate é que está errado (B01).

---

## 0. Ambiente de trabalho (leia antes de qualquer coisa)

### 0.1 venv fora do repositório
O Windows desta máquina está com `LongPathsEnabled=0` e o repositório fica num caminho de cerca de 195 caracteres. **Não crie `.venv` dentro do repo.**

```bash
python -m venv C:/v/ttt                      # caminho curto, fora do repo
C:/v/ttt/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt
```
(Antes do passo 1 o `requirements.txt` ainda é o antigo e não instala; use
`C:/v/ttt/Scripts/python -m pip install "torch==2.15.0" Flask==3.1.0 SQLAlchemy==2.0.36 python-dotenv==1.0.1 numpy==2.5.5 pytest==9.2.0`.)

### 0.2 Rodar pytest e o app por uma letra de drive curta (`subst`)
Partindo da raiz do repo, `tests/infrastructure_tests/databases_tests/repositories_test/player_repository_test.py` chega a 282 caracteres, acima do limite de 260. O pytest falha com um `ImportError` cuja mensagem é só o caminho. A solução, já testada, é mapear o repo numa letra de drive:

```powershell
subst T: "C:\Users\vinio\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\scratch-workspaces\ea839efe-b7a7-4785-92ad-0746174c9493\58e189da-21c7-46fb-a813-66ec973ddf1f\scratch-2026-11-23-e6aca0\tictactoe-api"
Set-Location T:\
$env:PYTHONDONTWRITEBYTECODE = "1"
C:\v\ttt\Scripts\python.exe -m pytest
# ao final:  Set-Location C:\ ; subst T: /D
```
Funciona no Git Bash também: `cd /t/`. O git funciona normalmente em `T:\`. Tudo em `docs/ACCEPTANCE_CRITERIA.md` assume que o diretório atual é `T:\` (a raiz do repo).

### 0.3 Build ou instalação limpa
Se precisar de `python -m build` ou de uma cópia limpa, extraia o HEAD num caminho curto:
`rm -rf C:/v/tts && mkdir C:/v/tts && git archive HEAD | tar -x -C C:/v/tts`.

### 0.4 Outras orientações
- `core.autocrlf=true` neste git. Não converta finais de linha em massa e não reformate arquivos que você não está mudando.
- Não troque de branch, não faça push, não mexa no GitHub. Faça um commit por passo da seção 6, com mensagens terminando em
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (ou a atribuição do seu próprio modelo, se o orquestrador pedir).

---

## 1. Revisão de arquitetura

O que já está **certo** e deve ficar como está: `app/domain` não importa infra, nem framework, nem as camadas externas. As entidades de domínio (`app/domain/entities`) são separadas dos modelos SQLAlchemy (`app/infra/db/entities`). As interfaces de repositório ficam no domínio. O PyTorch está confinado em `app/infra/ai` e escondido atrás de portas (`MLLearningInterface`, `MLMovementInterface`). A organização em camadas é boa; os problemas estão na ligação entre elas e no estado global.

| # | Gravidade | Onde (arquivo:linha) | Problema | Correção mínima |
|---|---|---|---|---|
| A1 | Alta | `app/interface/api/controllers/game_controller.py:6,17,30-31`; `ai_controller.py:3-4,13-14,27-28`; `player_controller.py:3,12` | Os controllers instanciam repositórios e adaptadores de IA da infra diretamente. Não há raiz de composição, então a interface depende da infra e não dá para trocar o banco ou o modelo nos testes. | Criar `app/container.py` com `build_container(config) -> Container` (dataclass com os use cases já montados). `create_app(config)` chama `build_container` e guarda o resultado em `app.extensions["container"]`. Os controllers só usam os use cases. Nenhum módulo em `app/interface` importa `app.infra`. |
| A2 | Alta | `app/infra/db/repositories/decorators.py:5-23`; `game_repository.py:14-16` e outros; `player_repository.py:12-13` e outros | Os repositórios são `@classmethod` e o decorator faz `setattr(cls, 'session', ...)`: estado mutável no nível da classe, que não é thread-safe (o servidor de desenvolvimento do Flask usa threads). Cada chamada faz `create_engine` de novo (`decorators.py:7`), com `echo=True` (`db_connection_handler.py:21`). | Repositórios baseados em instância, que recebem um `sessionmaker` no construtor e usam `with self._session_factory.begin()`. Um único engine por app, numa classe `app/infra/db/database.py:Database(url)` com `.engine`, `.session_factory` e `.create_tables()`. Remover `decorators.py`, `db_connection_handler.py` e `db_migrations_handler.py`. Sem `echo=True`. |
| A3 | Alta | `decorators.py:2,7`; `app/infra/ai/use_cases/ai_movement.py:6,18` | Os adaptadores leem configuração do ambiente por conta própria. | A configuração entra pelo construtor: `GameRepository(session_factory)`, `AILearning(model_path)`, `AIMovement(model_path)`. Só o container lê `Settings`. |
| A4 | Média | `app/domain/repositories/player_repository_interface.py:17` vs `app/infra/db/repositories/player_repository.py:50` | A porta `update_player` não tem `id`, mas o adaptador tem. O contrato está quebrado (e o use case passa `**vars(player)`, o que esconde o problema). | Portas trabalham com entidades: `update_player(player: Player) -> Player`, `create_game(game: Game) -> Game`, `update_game(game: Game) -> Game`. Ver as assinaturas na seção 5.3. |
| A5 | Média | `app/domain/services/game_service.py:4-60`; `player_service.py`; `app/application/use_cases/game_move_maker.py:9-23`; `game_controller.py:32-45` | Modelo de domínio anêmico. `GameService` é um "serviço" com estado, que embrulha uma única partida. `check_move_validity` tem que ser chamado antes de `make_move` (acoplamento temporal, `game_service.py:15-28`). O use case recebe `game` e também `GameService(game)`, o que é redundante. Quem busca a partida e monta os serviços de domínio é o controller. | Levar as regras para as entidades: `Game.play(row, column, mark)` valida e aplica a jogada e encerra a partida; `Player.record_result(winner)`. Apagar `app/domain/services/`. O use case recebe `player_id`, `row`, `column` e `value`, e carrega a partida sozinho. |
| A6 | Média | `app/domain/ml/ml_learning_interface.py:9`; `app/application/use_cases/ml_trainer.py:9-11`; `ai_controller.py:32`; `ai_movement.py:18` | Um detalhe de armazenamento (`pth_file_path`) vazou para a porta de domínio. Pior: o treino salva em `'tic_tac_toe_model.pth'` fixo e relativo ao diretório atual, enquanto a predição lê `ML_PATH_FILE_PATH`. O treino não afeta a predição, a não ser que os dois caminhos coincidam por acaso. | Porta `learn(games) -> int`. O caminho do modelo vem do construtor do adaptador e sai de uma única configuração (`ML_MODEL_PATH`). |
| A7 | Média | todos os controllers (`player_controller.py:20-21`, `game_controller.py:23-24,47-48`, `ai_controller.py:20-21,35-36`); `game_move_maker.py:18`; `env_vars_handler.py:11-20`; `game_repository.py:95-96` | Tratamento de erros. Todo erro vira 500 com `str(e)`, o que vaza detalhes internos e devolve o status errado. Jogada inválida responde **200** com `{'Message': ...}` (chave em maiúscula, diferente do `'message'` da resposta de sucesso). `verify_env` transforma erro em string e devolve essa string como valor de configuração. Uma regra de negócio é sinalizada com `ValueError` dentro do repositório. | Exceções de domínio em `app/domain/exceptions.py`, que é um contrato (seção 5.2). Os handlers centrais ficam em `app/interface/api/errors.py`: `DomainError` vira 400/404/409, a validação de entrada vira 400 e o resto vira um 500 genérico, com log. Nenhum `except Exception` que engula o erro. Repositório devolve `None` quando não acha, e o use case decide o que fazer. |
| A8 | Média | `main.py:6-9`; `app/infra/settings/env_vars_handler.py` | Configuração. O `.env` é lido relativo ao diretório atual e não há defaults. A conexão com o banco e a migração rodam no import. O nome `ML_PATH_FILE_PATH` é confuso. | `app/infra/settings/settings.py`: `Settings(db_connection_string, ml_model_path)` e `load_settings(overrides)`, com precedência overrides > ambiente (inclui o `.env` do cwd, via `load_dotenv(override=False)`) > defaults (`sqlite:///tictactoe.db`, `models/tictactoe_model.pth`). Renomear para `ML_MODEL_PATH`. |
| A9 | Média | `app/infra/ai/use_cases/` | Uma pasta "use_cases" dentro da infra confunde as camadas: aquilo são adaptadores. | Mover para `app/infra/ai/learning.py` (`AILearning`), `app/infra/ai/movement.py` (`AIMovement`) e `app/infra/ai/dataset.py` (contrato, seção 5.5). Apagar `app/infra/ai/use_cases/` e `app/infra/ai/services/`. |
| A10 | Baixa | `game_repository.py:23-24,34-35,53-54,72-75,97-98,124-130` | `board` e `movements` são gravados com `str()` e lidos com `ast.literal_eval`. `is not 'None'` compara identidade de string (dá `SyntaxWarning` no 3.12+) e só funciona por acaso. O mapeamento ORM→entidade está duplicado 5 vezes. Os campos de estatística são nullable (`infra/db/entities/player.py:14-16`), por isso a API devolve `null`. | Colunas `JSON` do SQLAlchemy, uma única `_to_entity(row)` por repositório e estatísticas `nullable=False, default=0`. |
| A11 | Baixa | `app/infra/db/entities/__init__.py:1`; `db_migrations_handler.py:4,9,13` | `sqlalchemy.ext.declarative.declarative_base` está deprecated (MovedIn20Warning) e é usado como anotação de tipo. | `from sqlalchemy.orm import declarative_base`. A classe `Database` substitui os handlers. |
| A12 | Baixa | `app/infra/ai/models/tictactoe_nn_model.py:10,15` | `Softmax` na saída e `CrossEntropyLoss` no treino, ou seja, softmax aplicado duas vezes. | `forward` devolve logits. A inferência usa argmax sobre as casas vazias. |
| A13 | Baixa | `app/domain/entities/__init__.py:3`; `game_starter.py:12` | `Board` é uma tupla de listas, que vira tupla de novo depois do `literal_eval`. Não serializa de forma estável. | `Board = List[List[int]]`. A entidade copia para listas no construtor. |
| A14 | Info | `app/interface/api/__init__.py:7` | `JSONIFY_PRETTYPRINT_REGULAR` não tem efeito desde o Flask 2.3. | Remover. |

**O que eu NÃO mudaria** (seria refatorar por gosto): o nome do pacote `app`, a separação domain/application/infra/interface, as portas de ML continuarem em `app/domain/ml` (poderiam ir para `application/ports`, mas não há ganho que justifique), o Flask, o SQLAlchemy síncrono e a ausência de Alembic (`create_all` basta para o escopo do projeto).

### 1.1 Segurança
| # | Gravidade | Onde | Problema | Correção |
|---|---|---|---|---|
| S1 | Alta | `main.py:12` | `app.run(debug=True, host='0.0.0.0')` expõe o debugger do Werkzeug na rede, o que permite execução remota de código. | `host=os.getenv('HOST','127.0.0.1')`, `port=int(os.getenv('PORT','5000'))`, `debug=os.getenv('FLASK_DEBUG')=='1'`. A string `debug=True` não pode aparecer em `main.py` (AC-31). |
| S2 | Baixa | `.env` | Está versionado. O conteúdo são só caminhos de exemplo, não há segredo, então **não é preciso reescrever o histórico**. | `git rm --cached .env`, colocar no `.gitignore` e criar `.env.example`. |

---

## 2. Revisão de funcionalidade (regras do jogo e fluxo)

As regras do alvo, que fazem parte do contrato e estão codificadas nos testes:
- O jogador humano é **X = 1**, a IA é **O = -1**. **X sempre começa** e os turnos se alternam. O próximo a jogar é `1` se `len(movements)` for par, senão `-1`.
- Uma jogada só é válida se: a partida está `in_progress`; `row` e `column` são `int` (não `bool`) entre 0 e 2; `value` é 1 ou -1 e é o próximo a jogar; a casa está vazia.
- Depois de cada jogada: **primeiro** verifica a vitória do autor da jogada (3 linhas, 3 colunas, 2 diagonais). Se ele venceu, `state='finished'` e `winner=mark`. **Senão**, se o tabuleiro está cheio, `state='finished'` e `winner=0` (empate). Enquanto a partida está em andamento, `winner=0`.
- No fim da partida, as estatísticas do jogador são atualizadas (vitória se `winner==1`, derrota se `-1`, empate se `0`).
- Cada jogador tem **no máximo uma** partida `in_progress`.

Cobertura atual: os 7 testes existentes não verificam nada (não têm `assert`) e não rodam fora da máquina do autor. Na prática a cobertura é **zero**.

---

## 3. Bugs encontrados (cada um tem teste de regressão em `tests/acceptance/test_regressions.py`)

Reproduções feitas contra o código atual, rodando o fixture de aceite com um shim de diagnóstico fora do repo, que define as variáveis de ambiente e cria as tabelas. "Atual" é o que o código faz hoje.

| Bug | Onde | Reprodução (via API) | Atual | Esperado | Teste |
|---|---|---|---|---|---|
| B01 | `app/domain/services/game_service.py:24-27` (empate é verificado antes da vitória) | X(0,0) O(0,1) X(0,2) O(1,0) X(1,1) O(1,2) X(2,1) O(2,0) X(2,2): a 9ª jogada fecha a diagonal | `winner=0` (empate), conta `draws` | `winner=1`, conta `victories` | `test_b01_*` |
| B02 | `game_service.py:17,31-32` (sem checagem de faixa) | `POST /api/move` com `row=-1` | 200, e **grava na linha 2** (índice negativo do Python) | 400 `invalid_movement`, tabuleiro intacto | `test_b02_*` |
| B03 | idem | `row=3` ou `column=3` | 500 (IndexError) | 400 `invalid_movement` | `test_b03_*` |
| B04 | `game_service.py:31-32` | `value` igual a 0, 2, 5, -2, `"x"` ou `null` | 200 (grava 5 no tabuleiro); `null` dá 500 | 400 `invalid_movement` | `test_b04_*` |
| B05 | não existe controle de turno | X abre com `value=-1`, ou X joga duas vezes seguidas | 200 | 409 `not_your_turn` | `test_b05_*` |
| B06 | `app/application/use_cases/game_move_maker.py:17-18` | jogar numa casa ocupada | **200** `{"Message":"Invalid movement"}` | 409 `cell_occupied` | `test_b06_*` |
| B07 | `game_repository.py:95-96` | jogar depois que a partida terminou | 500 `There is no game in progress` | 409 `game_finished` | `test_b07_*` |
| B08 | `game_starter.py:9-17` (o SQLite não aplica FK por padrão) | `POST /api/start` com `player_id=999999` | 201, cria partida para um jogador que não existe | 404 `player_not_found` | `test_b08_*` |
| B09 | `game_starter.py` | `POST /api/start` duas vezes | 201 e duas partidas `in_progress`; as jogadas vão para a mais antiga (`.first()`) | 409 `game_already_in_progress` | `test_b09_*` |
| B10 | `player_repository.py:20-21` | registrar o mesmo `nickname` duas vezes | 500 (IntegrityError) | 409 `nickname_taken` | `test_b10_*` |
| B11 | `player_controller.py`, `game_controller.py` | corpo `{}`, campos faltando, `nickname` vazio ou numérico, corpo que não é JSON | 500 ou 201 (aceita `nickname=""` e `123`) | 400 `validation_error` | `test_b11_*` |
| B12 | `game_repository.py:95-96` | `POST /api/move` para um jogador que nunca jogou | 500 | 404 `game_not_found` | `test_b12_*` |
| B13 | não existe endpoint de leitura de jogador; `player_repository.py:36` faz `.get(id)` sem tratar `None` | `GET /api/players/999999` | 404 do Flask, sem o corpo de erro do contrato | 404 `player_not_found` | `test_b13_*` |
| B14 | `ai_controller.py:12,17` (`int(None)`) | `GET /api/ai-move` sem `player-id`, com `player-id` vazio ou `abc` | 500 | 400 `validation_error` | `test_b14_*` |
| B15 | `ai_movement.py:25-28` | `ai-move` antes de qualquer treino | 500 (FileNotFoundError) | 409 `model_not_trained` | `test_b15_*` |
| B16 | `ai_learning.py:36`; `dataset_creator_service.py:24` | treinar com partidas que O venceu | 500 `Target -1 is out of bounds.` | 200 | `test_b16_*` |
| B17 | `ai_controller.py:32` | treinar e conferir onde o modelo foi salvo | salva em `./tic_tac_toe_model.pth`, ignorando a configuração | salva em `ML_MODEL_PATH`, criando as pastas | `test_b17_*` |
| B18 | `ai_controller.py:26-33` | `amount` igual a 0, -1, `"x"`, `null` ou 1.5 | 500 ou treino sem dados | 400 `validation_error` | `test_b18_*` |
| B19 | `game_repository.py:69` (`limit` sem filtro de estado) | treinar quando só existem partidas em andamento | 500 (dataset vazio ou partida parcial) | 409 `no_training_data` | `test_b19_*` |
| B20 | `dataset_creator_service.py:23-27` (`return` **dentro** do `for`) e o desenho do dataset | `DatasetCreatorService(games).create_dataset()` com 3 partidas | usa só a 1ª partida, e com tabuleiro **final** rotulado pelo vencedor (-1/0/1). Não aprende jogadas | ver o contrato na seção 5.5 | `test_b20_*` |

Problemas adicionais sem teste dedicado (são cobertos pelos fluxos ou por critérios estáticos):
- B21 `game_repository.py:69`: `get_games` pega as **primeiras** N partidas (as mais antigas), incluindo as que estão em andamento. O alvo são as N partidas `finished` **mais recentes**.
- B22 `ai_movement.py:41-49`: com o tabuleiro cheio devolve `None`, e a API responde `200 null`. O alvo é 409 `game_finished`, porque não existe partida em andamento para sugerir.
- B23 `ml_move_maker.py:28-29`: a IA recebe o tabuleiro cru, sem saber de quem é a vez. O alvo é sugerir para quem está na vez, com o tabuleiro visto pela perspectiva dele.
- B24 `requirements.txt:27-29`: `torch==2.5.1` não instala no 3.13 do Windows. `torchvision` e `torchaudio` não são usados. `pytest` está entre as dependências de runtime.
- B25 `README.md:73`: sobrou um "Copiar código" dentro do bloco bash. O README manda usar caminhos absolutos `C:\Users\you\...`.
- B26 testes existentes: sem `assert`, com caminho absoluto da máquina do autor, dependentes de dados que já precisam existir no banco, e `player_creator_test`/`player_repository_test` criam o mesmo nickname `Mr. Smith` (a segunda execução falharia).
- B27 `game_repository.py:35,54,98,130`: `SyntaxWarning: "is not" with 'str' literal`.

---

## 4. Renomeação `tictactoe_python_api` → `tictactoe-api`

Constatação: a string literal `tictactoe_python_api` **não aparece** em nenhum arquivo versionado. Os nomes antigos que existem de fato são:
- `README.md:1`: `# Tic Tac Toe Python API`
- `tictactoe_api`, em caminhos absolutos: `README.md:18-19`, `.env:1-2` e as 7 chamadas `read_env_vars('C:/Users/vinio/Projects/tictactoe_api/.env')` em `tests/application_tests/*` e `tests/infrastructure_tests/*`.

Decisões:
- Título do README: `# tictactoe-api`, na primeira linha.
- `pyproject.toml` novo com `[project] name = "tictactoe-api"`, `version = "1.0.0"`, `requires-python = ">=3.11"` e `[tool.pytest.ini_options] testpaths = ["tests"]`. Não precisa de `[build-system]`, o projeto não é instalado como pacote.
- `GET /api/health` responde `{"status": "ok", "name": "tictactoe-api"}`.
- O pacote Python continua `app`. Renomear o pacote obrigaria a mudar todos os imports e não traz nenhum benefício. O `import_name` do Flask continua `__name__`, porque o Flask o usa para localizar recursos.
- Nenhuma ocorrência (sem diferenciar maiúsculas) de `tictactoe_python_api`, `tictactoe_api` ou `tic tac toe python api` fora de `docs/` e `tests/acceptance/` (AC-05).
- O remote já aponta para `marcusstinghel/tictactoe-api`. Os links no README podem usar essa URL.

---

## 5. Decisões e contratos (os testes de aceite dependem disto)

### 5.1 API HTTP
Todas as rotas ficam sob `/api`. As rotas existentes foram mantidas e duas foram adicionadas.

| Método | Rota | Corpo/query | Sucesso |
|---|---|---|---|
| GET | `/api/health` | | 200 `{"status":"ok","name":"tictactoe-api"}` |
| POST | `/api/register` | `{"first_name","last_name","nickname"}`, todos strings não vazias | 201 Player |
| GET | `/api/players/<int:id>` | | 200 Player |
| POST | `/api/start` | `{"player_id": int}` | 201 Game |
| POST | `/api/move` | `{"player_id": int, "movement": {"row","column","value"}}` | 200 `{"message": str, "game": Game}` |
| GET | `/api/ai-move?player-id=<int>` | | 200 `{"row": int, "column": int, "position": row*3+column}`. É **somente leitura**: não aplica a jogada |
| POST | `/api/ai-train` | `{"amount": int > 0}` | 200 `{"message": str, "samples": int}` |

- Player: `{"id","first_name","last_name","nickname","victories","defeats","draws"}`. As estatísticas são inteiros e começam em 0.
- Game: `{"id","player_id","board" (lista 3x3 de int),"state" ("in_progress"|"finished"),"winner" (-1|0|1),"movements" (lista de {"row","column","value"}, [] no início)}`.
- `ai-move` sugere a jogada para **quem está na vez** (normalmente O, depois que o humano joga). O cliente então faz `POST /api/move` com `value=-1`. Ordem das checagens: validar `player-id` (400) → jogador existe (404) → partida atual (404/409) → modelo existe (409).
- Em `/api/move`, ordem: corpo/tipos do envelope (`validation_error` 400) → jogador (404) → partida atual (404 `game_not_found` ou 409 `game_finished`) → regras de domínio.
- "Partida atual" de um jogador: a `in_progress` dele. Se não houver nenhuma mas existir partida terminada, `game_finished` (409). Se ele nunca jogou, `game_not_found` (404).

### 5.2 Contrato de erro
Corpo de erro: `{"error": {"code": "<code>", "message": "<texto>"}}`.

| code | status | origem |
|---|---|---|
| `validation_error` | 400 | interface: corpo que não é JSON, campo faltando ou com tipo errado, `player-id` ou `amount` inválidos |
| `invalid_movement` | 400 | domínio: linha/coluna fora de 0..2 ou sem ser int; `value` diferente de ±1 |
| `player_not_found` | 404 | domínio |
| `game_not_found` | 404 | domínio |
| `not_your_turn` | 409 | domínio |
| `cell_occupied` | 409 | domínio |
| `game_finished` | 409 | domínio |
| `game_already_in_progress` | 409 | domínio |
| `nickname_taken` | 409 | domínio (a infra converte o `IntegrityError`) |
| `model_not_trained` | 409 | domínio (lançado pelo adaptador de IA) |
| `no_training_data` | 409 | domínio |
| `internal_error` | 500 | handler genérico. Mensagem fixa, nunca `str(e)`. Registrar com `logger.exception` |

`app/domain/exceptions.py` define `DomainError(Exception)` com o atributo de classe `code` e `message`, e uma subclasse por código de domínio acima (pelo menos 4, AC-17). O mapeamento classe→status fica **só** em `app/interface/api/errors.py`, porque o domínio não conhece HTTP. 404/405 do Flask também devem sair no formato de erro (via handler de `HTTPException`).

### 5.3 Portas (assinaturas exatas; AC-15 compara os nomes dos parâmetros da porta com os do adaptador)
```python
# app/domain/repositories/player_repository_interface.py
create_player(self, first_name: str, last_name: str, nickname: str) -> Player   # lança NicknameTaken
get_player(self, id: int) -> Optional[Player]
update_player(self, player: Player) -> Player
# app/domain/repositories/game_repository_interface.py
create_game(self, game: Game) -> Game
get_in_progress_game(self, player_id: int) -> Optional[Game]
get_latest_game(self, player_id: int) -> Optional[Game]
get_finished_games(self, limit: int) -> List[Game]        # as mais recentes primeiro
update_game(self, game: Game) -> Game
# app/domain/ml/ml_learning_interface.py
learn(self, games: List[Game]) -> int                      # nº de amostras; lança NoTrainingData
# app/domain/ml/ml_movement_interface.py
make_move(self, board: List[int]) -> int                    # 9 casas na perspectiva de quem joga; lança ModelNotTrained
```
Os adaptadores são **métodos de instância comuns**, sem `@classmethod` e sem decorator que esconda a assinatura. Nenhum adaptador atribui `cls.algo = ...` nem chama `setattr(cls, ...)` (AC-16).

### 5.4 Entidades
- `Game(id, state, player_id, movements, winner, board)` é chamado **por keyword**, e o teste B20 constrói `Game` assim. Mantenha esses 6 nomes. Também: `Game.new(player_id)`, `next_mark`, `is_finished`, `flat_board()`, `play(row, column, mark)` e `to_dict()`.
- `Player(id, first_name, last_name, nickname, victories=0, defeats=0, draws=0)`, com `record_result(winner)` e `to_dict()`.

### 5.5 IA (treino e jogada)
- `app/infra/ai/dataset.py: build_training_samples(games) -> list[tuple[list[int], int]]`, uma **função pura** (o teste B20 a importa por esse caminho):
  - ignora partidas que não estão `finished`;
  - percorre `movements` na ordem e mantém um tabuleiro de 9 casas que começa vazio;
  - para cada jogada de `mark` em (row, col): se `winner != 0` e `mark == winner`, **ou** se `winner == 0` (empate), emite a amostra `([casa * mark para cada casa do tabuleiro ANTES da jogada], row*3+col)`;
  - ordem: partidas na ordem recebida, jogadas na ordem em que foram feitas.
- `AILearning(model_path, epochs=30, seed=0).learn(games)`: monta as amostras e lança `NoTrainingData` se não houver nenhuma. Faz `torch.manual_seed(seed)`, usa `CrossEntropyLoss` com alvos `long` entre 0 e 8 e Adam. Antes de `torch.save(state_dict, model_path)` cria as pastas pai (o teste usa um caminho `.../model/acceptance_model.pth` que ainda não existe).
- `AIMovement(model_path).make_move(board)`: se o arquivo não existe, lança `ModelNotTrained`. Carrega com `torch.load(..., weights_only=True)` e faz argmax dos logits **restrito às casas vazias**.
- `MLMoveMaker`: `mark = game.next_mark` e `board = [c * mark for c in game.flat_board()]`. Se o adaptador devolver uma casa ocupada, recai na primeira casa vazia (a regra não fica na mão do adaptador). Devolve `(row, column)`.
- `MLTrainer.train(games_amount)`: chama `get_finished_games(limit=games_amount)`. Se a lista vier vazia, lança `NoTrainingData`. Senão chama `learn`.
- O modelo `TictactoeNNModel` passa a `forward` → logits (camada oculta de 36 neurônios, por exemplo). O arquivo `.pth` antigo é incompatível e foi treinado com o pipeline quebrado.

### 5.6 Configuração e artefatos
- Variáveis: `DB_CONNECTION_STRING` (default `sqlite:///tictactoe.db`) e `ML_MODEL_PATH` (default `models/tictactoe_model.pth`). Os caminhos relativos são relativos ao diretório atual.
- `create_app(config: Mapping | None = None)` em `app/interface/api/__init__.py`: as chaves de `config` têm os mesmos nomes das variáveis e prevalecem sobre o ambiente. Também chama `app.config.update(config)` e cria as tabelas, via `build_container` → `Database.create_tables()`.
- `main.py`: `app = create_app()` no nível do módulo, para `flask --app main run` e para o smoke test. `app.run(...)` fica no `if __name__ == "__main__"`, com host, porta e debug vindos do ambiente (S1).
- `.env` sai do índice (`git rm --cached .env`). `.env.example` é versionado, com as duas variáveis e valores relativos.
- `tic_tac_toe_model.pth` sai do índice e do disco do repo, porque é um artefato gerado e está corrompido semanticamente (B20). Sem modelo treinado, `ai-move` responde 409 `model_not_trained`, e o README explica como jogar algumas partidas e depois treinar.
- `.gitignore`: `venv/`, `.venv/`, `__pycache__/`, `*.pyc`, `.idea/`, `.pytest_cache/`, `.env`, `*.db`, `*.pth`, `models/`.
- `requirements.txt` só com as dependências diretas de runtime, fixadas nas versões verificadas aqui no 3.13/Windows: `Flask==3.1.0`, `SQLAlchemy==2.0.36`, `python-dotenv==1.0.1`, `numpy==2.5.5`, `torch==2.15.0`. Nada de pytest, torchvision, torchaudio, aiosqlite, pillow. `requirements-dev.txt` contém `pytest==9.2.0`. Uma instalação limpa num venv novo com essas versões passou, e o protótipo rodou 90 testes verdes com elas.
- Schema: as colunas `board`/`movements` passam a ser `JSON`. Um `tictactoe.db` antigo é incompatível: apague. Não vamos adicionar Alembic.

### 5.7 CI: **sim**
`.github/workflows/ci.yml`: em `push` e `pull_request`, `ubuntu-latest`, `actions/setup-python@v5` com `python-version: "3.13"` e `cache: pip`. Primeiro `pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu`, que evita os ~2 GB das wheels CUDA. Depois `pip install -r requirements.txt -r requirements-dev.txt` e `python -m pytest`. O motivo: é o principal projeto de portfólio, o custo é nulo e a suíte não usa rede nem arquivos externos. Não é preciso rodar o CI agora, porque não haverá push.

### 5.8 Testes do projeto (fora de `tests/acceptance`)
Apague `tests/application_tests/` e `tests/infrastructure_tests/`, que são irrecuperáveis (B26) e têm caminhos acima de MAX_PATH. Crie testes rasos e com `assert` de verdade:
- `tests/unit/test_game_rules.py`: `Game.play`, todas as exceções, vitória na última casa, `Player.record_result`;
- `tests/integration/test_repositories.py`: os repositórios num SQLite em `tmp_path`, ida e volta de `board`/`movements`, `NicknameTaken`.
Mantenha `tests/__init__.py`. Use nomes curtos (pasta+arquivo com menos de 60 caracteres a partir da raiz).

---

## 6. Passos (pequenos e verificáveis; um commit por passo)

Execute na ordem. Ao final de cada passo rode o que está indicado. O código intermediário pode quebrar outros testes de aceite, mas **não** os que o passo promete.

1. **Higiene do repositório.** `git rm --cached .env tic_tac_toe_model.pth` e apagar o `.pth` do disco. Novo `.gitignore` (5.6), `.env.example`, `requirements.txt`, `requirements-dev.txt` e `pyproject.toml` (seção 4). Instale num venv novo e curto (`C:/v/ttc`).
   Verificar: AC-01, AC-02, AC-03, AC-04, AC-07, AC-09.
2. **Domínio.** Criar `app/domain/exceptions.py`. Reescrever `Game` e `Player` (5.4) com as regras da seção 2. Apagar `app/domain/services/`. Atualizar as portas (5.3). Criar `tests/unit/test_game_rules.py`.
   Verificar: `pytest tests/unit`, `pytest tests/acceptance/test_architecture.py -k "domain"` (AC-10, AC-17 em parte).
3. **Infra de banco.** `app/infra/db/database.py`, modelos com JSON e estatísticas não nulas, e os repositórios por instância com `_to_entity`. Apagar `decorators.py` e `app/infra/db/settings/`. Criar `tests/integration/test_repositories.py`.
   Verificar: `pytest tests/integration`.
4. **Infra de IA.** `dataset.py` (5.5), `learning.py`, `movement.py` e o modelo devolvendo logits. Apagar `app/infra/ai/use_cases/` e `app/infra/ai/services/`.
   Verificar: `pytest tests/acceptance/test_regressions.py -k b20`.
5. **Settings e container.** `app/infra/settings/settings.py` (e apagar `env_vars_handler.py`), `app/container.py`.
   Verificar: AC-14 e o `test_composition_root_exists`.
6. **Application.** Ajustar os use cases: `PlayerCreator`, `PlayerFinder`, `GameStarter(game_repo, player_repo)`, `GameMoveMaker(game_repo, player_repo)`, `MLTrainer`, `MLMoveMaker(game_repo, player_repo, ml_movement)`. Colocar num helper compartilhado (`require_player`, `current_game`) a regra de "partida atual" (5.1).
   Verificar: AC-11.
7. **Interface.** `create_app(config)`, `errors.py` (5.2), controllers que só validam o envelope e chamam use cases, e as rotas novas `/health` e `/players/<id>`. Apagar `app/interface/api/controllers/` e `routes/` se você os achatar; é opcional, desde que nenhum arquivo importe `app.infra`.
   Verificar: AC-12, AC-20…AC-29.
8. **Entrada do app.** `main.py` (S1, 5.6).
   Verificar: AC-31, AC-32.
9. **Testes antigos.** Apagar `tests/application_tests/` e `tests/infrastructure_tests/`.
   Verificar: AC-19, AC-06.
10. **README.** Reescrever do zero. Título `# tictactoe-api`, uma descrição curta, e "Como rodar do zero" num shell limpo: clonar, criar o venv, `pip install -r requirements.txt -r requirements-dev.txt`, `cp .env.example .env` (opcional), `python main.py`, `curl http://127.0.0.1:5000/api/health` e rodar `pytest`. Incluir a tabela de rotas (5.1), o contrato de erro (5.2), o fluxo de partida completo com curl (registrar → start → move… → ai-train → ai-move → move com `value=-1`), a explicação do treino (5.5) e o badge do CI. Usar só caminhos relativos e tirar o "Copiar código".
   Verificar: AC-05, AC-06, AC-08.
11. **CI.** `.github/workflows/ci.yml` (5.7).
    Verificar: AC-30.
12. **Verificação final.** Todos os critérios de `docs/ACCEPTANCE_CRITERIA.md`, de AC-01 a AC-35, num venv limpo.

---

## 7. Riscos e armadilhas para quem implementa
- **MAX_PATH**: sem o `subst T:` (0.2) o pytest falha com um `ImportError` sem explicação. Arquivos `.pyc` em caminhos longos falham sem aviso, e por isso existe o `PYTHONDONTWRITEBYTECODE=1`.
- **Torch**: não use `torch==2.5.1`. No CI, use o índice CPU, senão o job baixa gigabytes.
- **SQLite + threads**: crie um único engine por app (`Database`). Não crie engine por chamada.
- **Sessões**: use `sessionmaker(expire_on_commit=False)` ou converta para entidade **antes** de fechar a sessão. Senão aparece `DetachedInstanceError` ao ler atributos depois do commit.
- **Colunas JSON**: ao atualizar `board`, atribua uma lista **nova** (`[list(r) for r in game.board]`). Mutar no lugar não é detectado pelo SQLAlchemy.
- **`bool` é `int` em Python**: `True` não pode passar como linha/coluna/valor. Use `isinstance(v, int) and not isinstance(v, bool)`.
- **`pytest.ini`/`conftest` na raiz**: não crie um `conftest.py` na raiz que mexa em `create_app` ou nas variáveis de ambiente. Os testes de aceite isolam tudo sozinhos (cwd temporário e variáveis removidas).
- **Teste de assinaturas (AC-15)**: compara os **nomes** dos parâmetros, sem `self`. Se renomear `id` para `player_id` num lado só, ele falha.
- **AC-14** procura as strings `getenv` e `os.environ` em `app/infra/ai` e `app/infra/db/repositories`, e a string `pth` (sem diferenciar maiúsculas) em `app/domain` e `app/application`. Evite essas palavras até em comentários.
- **AC-17** proíbe `except Exception:` ou `except:` sem `raise` dentro do handler, em qualquer arquivo de `app/`. Use `@app.errorhandler(Exception)`.
- **Smoke (AC-32)**: sobe `python main.py` num diretório temporário, com `PYTHONPATH` na raiz do repo e `PORT` livre. Então `main.py` precisa respeitar a variável `PORT`.
- Os testes de aceite com as sequências de jogadas assumem que X começa. Não mude essa regra.

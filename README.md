# tictactoe-api

[![CI](https://github.com/marcusstinghel/tictactoe-api/actions/workflows/ci.yml/badge.svg)](https://github.com/marcusstinghel/tictactoe-api/actions/workflows/ci.yml)

A Flask API for Tic Tac Toe: players, games with full rule enforcement, per-player statistics and an AI opponent (PyTorch) that learns from the finished games stored in the database.

The code follows Clean Architecture: `app/domain` (entities, rules, ports), `app/application` (use cases), `app/infra` (SQLAlchemy and PyTorch adapters), `app/interface` (Flask) and `app/container.py`, the only place where infrastructure is wired into the use cases.

## Running from scratch

Requires Python 3.11 or newer (tested on 3.13).

```bash
git clone https://github.com/marcusstinghel/tictactoe-api.git
cd tictactoe-api
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env              # optional, the defaults are the same
python main.py
```

In another shell:

```bash
curl http://127.0.0.1:5000/api/health
```

Run the tests with:

```bash
python -m pytest
```

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DB_CONNECTION_STRING` | `sqlite:///tictactoe.db` | SQLAlchemy URL. Tables are created on start. |
| `ML_MODEL_PATH` | `models/tictactoe_model.pth` | Where training saves the model and where `ai-move` loads it. Folders are created. |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Used by `python main.py`. |
| `FLASK_DEBUG` | unset | Set to `1` to enable the debugger and reloader. Never expose it on a public host. |

Precedence: process environment, then a `.env` file in the current directory, then the defaults. Relative paths are relative to the current directory. An old `tictactoe.db` created by a previous version is incompatible: delete it.

## API

All routes live under `/api`.

| Method | Route | Body / query | Success |
|---|---|---|---|
| `GET` | `/api/health` | | `200 {"status": "ok", "name": "tictactoe-api"}` |
| `POST` | `/api/register` | `{"first_name", "last_name", "nickname"}` (non-empty strings) | `201` player |
| `GET` | `/api/players/<id>` | | `200` player |
| `POST` | `/api/start` | `{"player_id": int}` | `201` game |
| `POST` | `/api/move` | `{"player_id": int, "movement": {"row", "column", "value"}}` | `200 {"message", "game"}` |
| `GET` | `/api/ai-move?player-id=<int>` | | `200 {"row", "column", "position"}` (read-only) |
| `POST` | `/api/ai-train` | `{"amount": int > 0}` | `200 {"message", "samples"}` |

Rules: the human is X (`value` 1) and always starts, the AI is O (`value` -1), turns alternate, `row` and `column` go from 0 to 2. A win is checked before a full board, so a win on the ninth move is a win. Each player has at most one game in progress. Statistics (`victories`, `defeats`, `draws`) are updated when a game ends.

A player is `{"id", "first_name", "last_name", "nickname", "victories", "defeats", "draws"}`. A game is `{"id", "player_id", "board" (3x3), "state" ("in_progress" or "finished"), "winner" (-1, 0 or 1), "movements" ([{"row", "column", "value"}])}`.

### Errors

Every error has the shape `{"error": {"code": "...", "message": "..."}}`.

| Code | Status | When |
|---|---|---|
| `validation_error` | 400 | Body is not JSON, a field is missing or has the wrong type, bad `player-id` or `amount` |
| `invalid_movement` | 400 | Row or column outside 0..2, or `value` not 1 or -1 |
| `player_not_found` | 404 | Unknown player |
| `game_not_found` | 404 | The player never started a game |
| `not_your_turn` | 409 | The mark that moved is not the one on turn |
| `cell_occupied` | 409 | The cell is taken |
| `game_finished` | 409 | The game already ended |
| `game_already_in_progress` | 409 | `start` while a game is in progress |
| `nickname_taken` | 409 | Duplicate nickname |
| `model_not_trained` | 409 | `ai-move` before any training |
| `no_training_data` | 409 | `ai-train` without finished games |
| `internal_error` | 500 | Unexpected failure (details only in the server log) |

### Playing a full game

```bash
curl -X POST http://127.0.0.1:5000/api/register -H 'Content-Type: application/json' \
  -d '{"first_name": "Ada", "last_name": "Lovelace", "nickname": "ada"}'
curl -X POST http://127.0.0.1:5000/api/start -H 'Content-Type: application/json' -d '{"player_id": 1}'
curl -X POST http://127.0.0.1:5000/api/move -H 'Content-Type: application/json' \
  -d '{"player_id": 1, "movement": {"row": 1, "column": 1, "value": 1}}'
# ... keep playing until the game finishes, then train the AI on the finished games:
curl -X POST http://127.0.0.1:5000/api/ai-train -H 'Content-Type: application/json' -d '{"amount": 50}'
# in a new game, after X moved, ask for the suggestion for O and play it with value -1:
curl 'http://127.0.0.1:5000/api/ai-move?player-id=1'
curl -X POST http://127.0.0.1:5000/api/move -H 'Content-Type: application/json' \
  -d '{"player_id": 1, "movement": {"row": 0, "column": 0, "value": -1}}'
```

## How the AI learns

There is no pre-trained model: until `ai-train` runs, `ai-move` answers `409 model_not_trained`. Play a few games first, then train.

`ai-train` takes the `amount` most recent finished games. For each one it replays the moves and keeps the ones worth imitating: every move of the winner, or every move of both sides in a draw. Each sample is the board before the move, seen by the side that moved (its own marks are 1), and the chosen cell (0 to 8). A small network (9 inputs, 36 hidden neurons, 9 logits) is trained with cross entropy and saved to `ML_MODEL_PATH`.

`ai-move` suggests a move for whoever is on turn, picking the highest-scoring empty cell. It does not apply the move: the client sends it with `POST /api/move`.

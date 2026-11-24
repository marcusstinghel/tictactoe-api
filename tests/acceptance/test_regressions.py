"""One regression test per bug listed in docs/REFACTOR_PLAN.md, section 3 (AC-26 and AC-28).

Error contract: every rejected request answers with a JSON body
``{"error": {"code": "<code>", "message": "<text>"}}`` and the status below.
"""
import pytest

from .support import DRAW, X_WINS_ON_LAST_CELL, X_WINS_ROW0, error_code


def _started(api):
    player_id = api.new_player_id()
    assert api.start(player_id).status_code == 201
    return player_id


def _board_after_rejection(api, player_id):
    """Plays a legal move to read the board back; returns the board before that move."""
    response = api.move(player_id, 0, 0, 1)
    assert response.status_code == 200
    board = response.get_json()["game"]["board"]
    board[0][0] = 0
    return board


# B01: win on the 9th move was reported as a draw (draw checked before win).
def test_b01_win_on_last_cell_is_victory_not_draw(api):
    player_id = _started(api)
    game = api.play(player_id, X_WINS_ON_LAST_CELL)
    assert game["state"] == "finished"
    assert game["winner"] == 1
    player = api.get_player(player_id).get_json()
    assert (player["victories"], player["draws"]) == (1, 0)


# B02: negative indexes wrapped around (row -1 wrote on row 2).
def test_b02_negative_index_is_rejected_and_board_untouched(api):
    player_id = _started(api)
    response = api.move(player_id, -1, 0, 1)
    assert response.status_code == 400
    assert error_code(response) == "invalid_movement"
    assert _board_after_rejection(api, player_id) == [[0, 0, 0], [0, 0, 0], [0, 0, 0]]


# B03: out-of-range index raised IndexError and answered 500.
@pytest.mark.parametrize("row,column", [(3, 0), (0, 3), (9, 9)])
def test_b03_out_of_range_index_is_400(api, row, column):
    player_id = _started(api)
    response = api.move(player_id, row, column, 1)
    assert response.status_code == 400
    assert error_code(response) == "invalid_movement"


# B04: any integer was accepted as a mark (e.g. 5).
@pytest.mark.parametrize("value", [0, 2, 5, -2, "x", None])
def test_b04_mark_must_be_1_or_minus_1(api, value):
    player_id = _started(api)
    response = api.move(player_id, 0, 0, value)
    assert response.status_code == 400
    assert error_code(response) == "invalid_movement"


# B05: no turn control; the same side could play twice and O could open.
def test_b05_turns_alternate_starting_with_x(api):
    player_id = _started(api)
    response = api.move(player_id, 0, 0, -1)
    assert response.status_code == 409
    assert error_code(response) == "not_your_turn"

    assert api.move(player_id, 0, 0, 1).status_code == 200
    response = api.move(player_id, 1, 1, 1)
    assert response.status_code == 409
    assert error_code(response) == "not_your_turn"
    assert api.move(player_id, 1, 1, -1).status_code == 200


# B06: occupied cell answered 200 {"Message": "Invalid movement"}.
def test_b06_occupied_cell_is_409(api):
    player_id = _started(api)
    assert api.move(player_id, 1, 1, 1).status_code == 200
    response = api.move(player_id, 1, 1, -1)
    assert response.status_code == 409
    assert error_code(response) == "cell_occupied"


# B07: a move after the game ended answered 500 ("There is no game in progress").
def test_b07_move_after_game_finished_is_409(api):
    player_id = _started(api)
    api.play(player_id, X_WINS_ROW0)
    response = api.move(player_id, 2, 2, -1)
    assert response.status_code == 409
    assert error_code(response) == "game_finished"


# B08: a game could be started for a player that does not exist (SQLite FK not enforced).
def test_b08_start_for_unknown_player_is_404(api):
    response = api.start(999_999)
    assert response.status_code == 404
    assert error_code(response) == "player_not_found"


# B09: a second in-progress game could be started; moves went to the oldest one.
def test_b09_second_game_in_progress_is_409(api):
    player_id = _started(api)
    response = api.start(player_id)
    assert response.status_code == 409
    assert error_code(response) == "game_already_in_progress"


# B10: duplicate nickname raised IntegrityError and answered 500.
def test_b10_duplicate_nickname_is_409(api):
    assert api.register(nickname="trinity").status_code == 201
    response = api.register(nickname="trinity")
    assert response.status_code == 409
    assert error_code(response) == "nickname_taken"


# B11: missing/invalid fields answered 500 with the raw exception text.
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"first_name": "A", "last_name": "B"},
        {"first_name": "A", "last_name": "B", "nickname": ""},
        {"first_name": "A", "last_name": "B", "nickname": 123},
    ],
)
def test_b11_register_validates_payload(client, payload):
    response = client.post("/api/register", json=payload)
    assert response.status_code == 400
    assert error_code(response) == "validation_error"


def test_b11_move_validates_payload(api):
    player_id = _started(api)
    for payload in ({}, {"player_id": player_id}, {"player_id": player_id, "movement": {"row": 0}}):
        response = api.client.post("/api/move", json=payload)
        assert response.status_code == 400, payload
        assert error_code(response) in {"validation_error", "invalid_movement"}


def test_b11_non_json_body_is_400(client):
    response = client.post("/api/register", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert error_code(response) == "validation_error"


# B12: move for a player with no game answered 500.
def test_b12_move_without_any_game_is_404(api):
    player_id = api.new_player_id()
    response = api.move(player_id, 0, 0, 1)
    assert response.status_code == 404
    assert error_code(response) == "game_not_found"


# B13: unknown player in GET answered 500 (AttributeError on None).
def test_b13_unknown_player_is_404(api):
    response = api.get_player(999_999)
    assert response.status_code == 404
    assert error_code(response) == "player_not_found"


# B14: ai-move without/with invalid player-id answered 500 (int(None)).
@pytest.mark.parametrize("query", ["", "?player-id=", "?player-id=abc"])
def test_b14_ai_move_requires_player_id(client, query):
    response = client.get("/api/ai-move" + query)
    assert response.status_code == 400
    assert error_code(response) == "validation_error"


# B15: ai-move with no trained model answered 500 (FileNotFoundError).
def test_b15_ai_move_without_model_is_409(api):
    player_id = _started(api)
    api.move(player_id, 0, 0, 1)
    response = api.ai_move(player_id)
    assert response.status_code == 409
    assert error_code(response) == "model_not_trained"


# B16: training crashed on games won by O (CrossEntropyLoss target -1).
def test_b16_training_with_o_wins_and_draws_succeeds(api, config):
    from .support import O_WINS_ROW1

    player_id = api.new_player_id()
    for sequence in (O_WINS_ROW1, DRAW, O_WINS_ROW1):
        assert api.start(player_id).status_code == 201
        api.play(player_id, sequence)
    response = api.train(10)
    assert response.status_code == 200, response.get_data(as_text=True)


# B17: training wrote to a hard-coded relative file, not to the configured model path.
def test_b17_training_writes_configured_model_path(api, config, isolated):
    from pathlib import Path

    player_id = api.new_player_id()
    assert api.start(player_id).status_code == 201
    api.play(player_id, X_WINS_ROW0)
    assert api.train(10).status_code == 200
    assert Path(config["ML_MODEL_PATH"]).is_file()
    assert not (isolated / "tic_tac_toe_model.pth").exists()


# B18: invalid amount answered 500 or trained on nothing.
@pytest.mark.parametrize("amount", [0, -1, "x", None, 1.5])
def test_b18_train_amount_must_be_positive_int(api, amount):
    response = api.train(amount)
    assert response.status_code == 400
    assert error_code(response) == "validation_error"


# B19: training with no finished game crashed (empty dataset).
def test_b19_train_without_finished_games_is_409(api):
    player_id = _started(api)
    api.move(player_id, 0, 0, 1)  # in-progress games must not be used for training
    response = api.train(10)
    assert response.status_code == 409
    assert error_code(response) == "no_training_data"


# B20: the dataset builder returned after the first game (return inside the loop)
# and used final boards labelled with the winner instead of moves.
def test_b20_dataset_uses_every_finished_game_and_its_moves():
    from app.domain.entities import Game
    from app.infra.ai.dataset import build_training_samples

    def moves(cells):
        value, out = 1, []
        for row, column in cells:
            out.append({"row": row, "column": column, "value": value})
            value = -value
        return out

    x_win = Game(id=1, player_id=1, state="finished", winner=1,
                 board=[[1, 1, 1], [-1, -1, 0], [0, 0, 0]], movements=moves(X_WINS_ROW0))
    draw = Game(id=2, player_id=1, state="finished", winner=0,
                board=[[1, -1, 1], [1, -1, -1], [-1, 1, 1]], movements=moves(DRAW))
    in_progress = Game(id=3, player_id=1, state="in_progress", winner=0,
                       board=[[1, 0, 0], [0, 0, 0], [0, 0, 0]], movements=moves([(0, 0)]))

    samples = build_training_samples([x_win, draw, in_progress])

    # 3 moves of the winner X + all 9 moves of the draw; the in-progress game is ignored.
    assert len(samples) == 3 + 9
    boards = [list(board) for board, _ in samples]
    targets = [target for _, target in samples]
    assert all(len(board) == 9 for board in boards)
    assert all(isinstance(t, int) and 0 <= t <= 8 for t in targets)

    # First sample: empty board, X plays (0, 0) -> index 0.
    assert boards[0] == [0] * 9 and targets[0] == 0
    # Second sample of the X win: board before X's 2nd move, seen by X (own marks = 1).
    assert boards[1] == [1, 0, 0, -1, 0, 0, 0, 0, 0] and targets[1] == 1
    # Draw, O's first move (0, 1): board seen by O, so X's mark at index 0 is -1.
    assert boards[4] == [-1, 0, 0, 0, 0, 0, 0, 0, 0] and targets[4] == 1

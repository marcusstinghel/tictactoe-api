"""Train the AI from played games and ask it for moves (criteria AC-27 and AC-29)."""
from .support import DRAW, O_WINS_ROW1, X_WINS_ROW0


def _seed_finished_games(api, player_id):
    for sequence in (X_WINS_ROW0, O_WINS_ROW1, DRAW, X_WINS_ROW0):
        assert api.start(player_id).status_code == 201
        api.play(player_id, sequence)


def _empty_cells(board):
    return {(r, c) for r in range(3) for c in range(3) if board[r][c] == 0}


def test_train_then_ai_suggests_a_legal_move_for_the_side_to_move(api):
    player_id = api.new_player_id()
    _seed_finished_games(api, player_id)

    response = api.train(50)
    assert response.status_code == 200, response.get_data(as_text=True)

    assert api.start(player_id).status_code == 201
    game = api.play(player_id, [(1, 1)])  # X played, now it's O's turn

    response = api.ai_move(player_id)
    assert response.status_code == 200, response.get_data(as_text=True)
    suggestion = response.get_json()
    assert set(suggestion) >= {"row", "column", "position"}
    assert (suggestion["row"], suggestion["column"]) in _empty_cells(game["board"])
    assert suggestion["position"] == suggestion["row"] * 3 + suggestion["column"]

    # The suggestion is directly playable as O (-1), closing the client loop.
    played = api.move(player_id, suggestion["row"], suggestion["column"], -1)
    assert played.status_code == 200


def test_ai_move_is_read_only(api):
    player_id = api.new_player_id()
    _seed_finished_games(api, player_id)
    assert api.train(50).status_code == 200
    api.start(player_id)
    before = api.play(player_id, [(0, 0)])

    for _ in range(3):
        assert api.ai_move(player_id).status_code == 200

    # Board unchanged: O can still play any cell that was empty before.
    after = api.move(player_id, 2, 2, -1).get_json()["game"]
    assert len(after["movements"]) == len(before["movements"]) + 1


def test_ai_move_for_finished_game_is_409(api):
    player_id = api.new_player_id()
    _seed_finished_games(api, player_id)
    assert api.train(50).status_code == 200
    response = api.ai_move(player_id)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "game_finished"


def test_ai_move_for_player_without_games_is_404(api):
    player_id = api.new_player_id()
    response = api.ai_move(player_id)
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "game_not_found"

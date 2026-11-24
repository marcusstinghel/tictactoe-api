"""End-to-end game flow through the HTTP API (criteria AC-20 to AC-25)."""
import pytest

from .support import DRAW, O_WINS_ROW1, X_WINS_ROW0

EMPTY_BOARD = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

LINES = {
    "row0": [(0, 0), (0, 1), (0, 2)],
    "row1": [(1, 0), (1, 1), (1, 2)],
    "row2": [(2, 0), (2, 1), (2, 2)],
    "col0": [(0, 0), (1, 0), (2, 0)],
    "col1": [(0, 1), (1, 1), (2, 1)],
    "col2": [(0, 2), (1, 2), (2, 2)],
    "diag": [(0, 0), (1, 1), (2, 2)],
    "anti": [(0, 2), (1, 1), (2, 0)],
}


def _x_wins_on(line):
    """X plays the line; O plays the first two cells outside it (O cannot win with 2)."""
    others = [(r, c) for r in range(3) for c in range(3) if (r, c) not in line][:2]
    return [line[0], others[0], line[1], others[1], line[2]]


def test_health_reports_project_name(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "name": "tictactoe-api"}


def test_register_returns_player_with_zeroed_stats(api):
    response = api.register(nickname="neo")
    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body["id"], int)
    assert body["nickname"] == "neo"
    assert (body["victories"], body["defeats"], body["draws"]) == (0, 0, 0)

    fetched = api.get_player(body["id"])
    assert fetched.status_code == 200
    assert fetched.get_json() == body


def test_start_returns_empty_in_progress_game(api):
    player_id = api.new_player_id()
    response = api.start(player_id)
    assert response.status_code == 201
    game = response.get_json()
    assert isinstance(game["id"], int)
    assert game["player_id"] == player_id
    assert game["board"] == EMPTY_BOARD
    assert game["state"] == "in_progress"
    assert game["winner"] == 0
    assert game["movements"] == []


def test_move_updates_board_and_history(api):
    player_id = api.new_player_id()
    api.start(player_id)
    response = api.move(player_id, row=1, column=2, value=1)
    assert response.status_code == 200
    game = response.get_json()["game"]
    assert game["board"] == [[0, 0, 0], [0, 0, 1], [0, 0, 0]]
    assert game["state"] == "in_progress"
    assert game["movements"] == [{"row": 1, "column": 2, "value": 1}]


@pytest.mark.parametrize("line_name", sorted(LINES))
def test_x_wins_on_every_line(api, line_name):
    player_id = api.new_player_id()
    assert api.start(player_id).status_code == 201
    game = api.play(player_id, _x_wins_on(LINES[line_name]))
    assert game["state"] == "finished"
    assert game["winner"] == 1
    assert len(game["movements"]) == 5


def test_full_flow_victory_defeat_draw_updates_stats(api):
    player_id = api.new_player_id()

    assert api.start(player_id).status_code == 201
    game = api.play(player_id, X_WINS_ROW0)
    assert (game["state"], game["winner"]) == ("finished", 1)

    assert api.start(player_id).status_code == 201
    game = api.play(player_id, O_WINS_ROW1)
    assert (game["state"], game["winner"]) == ("finished", -1)

    assert api.start(player_id).status_code == 201
    game = api.play(player_id, DRAW)
    assert (game["state"], game["winner"]) == ("finished", 0)
    assert all(0 not in row for row in game["board"])

    player = api.get_player(player_id).get_json()
    assert (player["victories"], player["defeats"], player["draws"]) == (1, 1, 1)


def test_game_is_not_finished_before_a_line_or_full_board(api):
    player_id = api.new_player_id()
    api.start(player_id)
    game = api.play(player_id, DRAW[:8])
    assert game["state"] == "in_progress"
    assert game["winner"] == 0

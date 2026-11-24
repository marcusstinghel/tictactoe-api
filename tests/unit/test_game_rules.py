import pytest

from app.domain.entities import Game, Player
from app.domain.exceptions import CellOccupied, GameFinished, InvalidMovement, NotYourTurn


def play_all(game, cells):
    mark = 1
    for row, column in cells:
        game.play(row, column, mark)
        mark = -mark


def test_new_game_is_empty_and_x_starts():
    game = Game.new(player_id=7)
    assert game.state == "in_progress"
    assert game.winner == 0
    assert game.movements == []
    assert game.flat_board() == [0] * 9
    assert game.next_mark == 1


def test_play_applies_move_and_alternates():
    game = Game.new(1)
    game.play(1, 2, 1)
    assert game.board[1][2] == 1
    assert game.movements == [{"row": 1, "column": 2, "value": 1}]
    assert game.next_mark == -1


@pytest.mark.parametrize(
    "row,column",
    [(-1, 0), (0, -1), (3, 0), (0, 3), (True, 0), (0, False), ("0", 0), (None, 0), (0.0, 0)],
)
def test_invalid_coordinates(row, column):
    with pytest.raises(InvalidMovement):
        Game.new(1).play(row, column, 1)


@pytest.mark.parametrize("mark", [0, 2, -2, True, "x", None])
def test_invalid_mark(mark):
    with pytest.raises(InvalidMovement):
        Game.new(1).play(0, 0, mark)


def test_wrong_turn():
    game = Game.new(1)
    with pytest.raises(NotYourTurn):
        game.play(0, 0, -1)
    game.play(0, 0, 1)
    with pytest.raises(NotYourTurn):
        game.play(1, 1, 1)


def test_occupied_cell():
    game = Game.new(1)
    game.play(1, 1, 1)
    with pytest.raises(CellOccupied):
        game.play(1, 1, -1)


def test_win_finishes_game_and_blocks_further_moves():
    game = Game.new(1)
    play_all(game, [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)])
    assert (game.state, game.winner) == ("finished", 1)
    with pytest.raises(GameFinished):
        game.play(2, 2, -1)


def test_win_on_last_cell_is_victory_not_draw():
    game = Game.new(1)
    play_all(game, [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 1), (2, 0), (2, 2)])
    assert (game.state, game.winner) == ("finished", 1)


def test_draw():
    game = Game.new(1)
    play_all(game, [(0, 0), (0, 1), (0, 2), (1, 1), (1, 0), (1, 2), (2, 1), (2, 0), (2, 2)])
    assert (game.state, game.winner) == ("finished", 0)


def test_player_record_result():
    player = Player(id=1, first_name="A", last_name="B", nickname="ab")
    player.record_result(1)
    player.record_result(-1)
    player.record_result(0)
    player.record_result(0)
    assert (player.victories, player.defeats, player.draws) == (1, 1, 2)

import pytest

from app.domain.entities import Game
from app.domain.exceptions import NicknameTaken
from app.infra.db.database import Database
from app.infra.db.repositories import GameRepository, PlayerRepository


@pytest.fixture
def repos(tmp_path):
    database = Database("sqlite:///" + (tmp_path / "repo.db").as_posix())
    database.create_tables()
    return PlayerRepository(database.session_factory), GameRepository(database.session_factory)


def test_player_round_trip_and_update(repos):
    players, _ = repos
    created = players.create_player("Ada", "Lovelace", "ada")
    assert created.id is not None
    assert (created.victories, created.defeats, created.draws) == (0, 0, 0)

    created.record_result(1)
    players.update_player(created)
    fetched = players.get_player(created.id)
    assert fetched.victories == 1
    assert players.get_player(999) is None


def test_duplicate_nickname_raises(repos):
    players, _ = repos
    players.create_player("Ada", "Lovelace", "ada")
    with pytest.raises(NicknameTaken):
        players.create_player("Other", "Person", "ada")


def test_game_round_trip_keeps_board_and_movements(repos):
    players, games = repos
    player = players.create_player("Ada", "Lovelace", "ada")
    game = games.create_game(Game.new(player.id))
    assert game.id is not None

    game.play(1, 1, 1)
    game.play(0, 0, -1)
    games.update_game(game)

    fetched = games.get_in_progress_game(player.id)
    assert fetched.board == [[-1, 0, 0], [0, 1, 0], [0, 0, 0]]
    assert fetched.movements == [{"row": 1, "column": 1, "value": 1}, {"row": 0, "column": 0, "value": -1}]
    assert isinstance(fetched.board[0], list)


def test_finished_games_are_most_recent_first(repos):
    players, games = repos
    player = players.create_player("Ada", "Lovelace", "ada")
    ids = []
    for _ in range(3):
        game = games.create_game(Game.new(player.id))
        game.state = "finished"
        games.update_game(game)
        ids.append(game.id)
    open_game = games.create_game(Game.new(player.id))

    finished = games.get_finished_games(limit=2)
    assert [g.id for g in finished] == [ids[2], ids[1]]
    assert games.get_latest_game(player.id).id == open_game.id
    assert games.get_in_progress_game(player.id).id == open_game.id

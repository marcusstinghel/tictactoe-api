from app.application.use_cases.helpers import current_game, require_player
from app.domain.entities import Game
from app.domain.repositories import GameRepositoryInterface, PlayerRepositoryInterface


class GameMoveMaker:
    def __init__(self, game_repository: GameRepositoryInterface, player_repository: PlayerRepositoryInterface):
        self._game_repository = game_repository
        self._player_repository = player_repository

    def make_move(self, player_id: int, row, column, value) -> Game:
        player = require_player(self._player_repository, player_id)
        game = current_game(self._game_repository, player_id)
        game.play(row, column, value)
        game = self._game_repository.update_game(game)
        if game.is_finished:
            player.record_result(game.winner)
            self._player_repository.update_player(player)
        return game

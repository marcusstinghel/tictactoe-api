from app.application.use_cases.helpers import require_player
from app.domain.entities import Game
from app.domain.exceptions import GameAlreadyInProgress
from app.domain.repositories import GameRepositoryInterface, PlayerRepositoryInterface


class GameStarter:
    def __init__(self, game_repository: GameRepositoryInterface, player_repository: PlayerRepositoryInterface):
        self._game_repository = game_repository
        self._player_repository = player_repository

    def start(self, player_id: int) -> Game:
        require_player(self._player_repository, player_id)
        if self._game_repository.get_in_progress_game(player_id=player_id) is not None:
            raise GameAlreadyInProgress()
        return self._game_repository.create_game(Game.new(player_id))

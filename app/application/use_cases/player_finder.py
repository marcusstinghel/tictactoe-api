from app.application.use_cases.helpers import require_player
from app.domain.entities import Player
from app.domain.repositories import PlayerRepositoryInterface


class PlayerFinder:
    def __init__(self, player_repository: PlayerRepositoryInterface):
        self._player_repository = player_repository

    def find(self, player_id: int) -> Player:
        return require_player(self._player_repository, player_id)

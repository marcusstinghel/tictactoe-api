from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import Game


class GameRepositoryInterface(ABC):

    @abstractmethod
    def create_game(self, game: Game) -> Game:
        pass

    @abstractmethod
    def get_in_progress_game(self, player_id: int) -> Optional[Game]:
        pass

    @abstractmethod
    def get_latest_game(self, player_id: int) -> Optional[Game]:
        pass

    @abstractmethod
    def get_finished_games(self, limit: int) -> List[Game]:
        """Most recent first."""

    @abstractmethod
    def update_game(self, game: Game) -> Game:
        pass

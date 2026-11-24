from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities import Player


class PlayerRepositoryInterface(ABC):

    @abstractmethod
    def create_player(self, first_name: str, last_name: str, nickname: str) -> Player:
        """Raises NicknameTaken when the nickname already exists."""

    @abstractmethod
    def get_player(self, id: int) -> Optional[Player]:
        pass

    @abstractmethod
    def update_player(self, player: Player) -> Player:
        pass

from abc import ABC, abstractmethod
from typing import List


class MLMovementInterface(ABC):

    @abstractmethod
    def make_move(self, board: List[int]) -> int:
        """board: 9 cells seen by the side to move (own marks are 1). Raises ModelNotTrained."""

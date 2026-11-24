from abc import ABC, abstractmethod
from typing import List

from app.domain.entities import Game


class MLLearningInterface(ABC):

    @abstractmethod
    def learn(self, games: List[Game]) -> int:
        """Trains on the games and returns the number of samples. Raises NoTrainingData."""

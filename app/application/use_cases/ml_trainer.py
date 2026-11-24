from app.domain.exceptions import NoTrainingData
from app.domain.ml import MLLearningInterface
from app.domain.repositories import GameRepositoryInterface


class MLTrainer:
    def __init__(self, game_repository: GameRepositoryInterface, ml_learning: MLLearningInterface):
        self._game_repository = game_repository
        self._ml_learning = ml_learning

    def train(self, games_amount: int) -> int:
        games = self._game_repository.get_finished_games(limit=games_amount)
        if not games:
            raise NoTrainingData()
        return self._ml_learning.learn(games=games)

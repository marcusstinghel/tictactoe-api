from pathlib import Path
from typing import List

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from app.domain.entities import Game
from app.domain.exceptions import NoTrainingData
from app.domain.ml import MLLearningInterface
from app.infra.ai.dataset import build_training_samples
from app.infra.ai.models import TictactoeNNModel


class AILearning(MLLearningInterface):

    def __init__(self, model_path: str, epochs: int = 30, seed: int = 0):
        self._model_path = Path(model_path)
        self._epochs = epochs
        self._seed = seed

    def learn(self, games: List[Game]) -> int:
        samples = build_training_samples(games)
        if not samples:
            raise NoTrainingData()

        torch.manual_seed(self._seed)
        boards = torch.tensor([board for board, _ in samples], dtype=torch.float32)
        targets = torch.tensor([target for _, target in samples], dtype=torch.long)
        loader = DataLoader(TensorDataset(boards, targets), batch_size=8, shuffle=True)

        model = TictactoeNNModel()
        model.train()
        optimizer = optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.CrossEntropyLoss()
        for _ in range(self._epochs):
            for batch_boards, batch_targets in loader:
                optimizer.zero_grad()
                loss = criterion(model(batch_boards), batch_targets)
                loss.backward()
                optimizer.step()

        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), self._model_path)
        return len(samples)

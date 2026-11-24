from pathlib import Path
from typing import List

import torch

from app.domain.exceptions import ModelNotTrained
from app.domain.ml import MLMovementInterface
from app.infra.ai.models import TictactoeNNModel


class AIMovement(MLMovementInterface):

    def __init__(self, model_path: str):
        self._model_path = Path(model_path)

    def make_move(self, board: List[int]) -> int:
        if not self._model_path.is_file():
            raise ModelNotTrained()
        model = TictactoeNNModel()
        model.load_state_dict(torch.load(self._model_path, weights_only=True))
        model.eval()
        with torch.no_grad():
            logits = model(torch.tensor(board, dtype=torch.float32))
        empty = [index for index, cell in enumerate(board) if cell == 0]
        if not empty:
            raise ValueError("the board has no empty cell")
        return max(empty, key=lambda index: logits[index].item())

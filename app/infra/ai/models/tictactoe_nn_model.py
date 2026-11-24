import torch.nn as nn


class TictactoeNNModel(nn.Module):
    """Maps a 9-cell board (own marks = 1) to one logit per cell."""

    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(9, 36)
        self.fc2 = nn.Linear(36, 9)
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.fc2(self.relu(self.fc1(x)))

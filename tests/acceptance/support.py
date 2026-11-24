"""Helpers and move sequences shared by the acceptance tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Api:
    """Thin helper over the Flask test client. It never hides status codes."""

    def __init__(self, client):
        self.client = client
        self._counter = 0

    def register(self, nickname=None, first_name="Ada", last_name="Lovelace"):
        self._counter += 1
        nickname = nickname or f"player-{self._counter}"
        return self.client.post(
            "/api/register",
            json={"first_name": first_name, "last_name": last_name, "nickname": nickname},
        )

    def new_player_id(self):
        response = self.register()
        assert response.status_code == 201, response.get_data(as_text=True)
        return response.get_json()["id"]

    def get_player(self, player_id):
        return self.client.get(f"/api/players/{player_id}")

    def start(self, player_id):
        return self.client.post("/api/start", json={"player_id": player_id})

    def move(self, player_id, row, column, value):
        return self.client.post(
            "/api/move",
            json={"player_id": player_id, "movement": {"row": row, "column": column, "value": value}},
        )

    def play(self, player_id, cells, first_value=1):
        """Plays the given (row, column) cells alternating X (1) and O (-1).

        Asserts each move is accepted and returns the last response's game.
        """
        value = first_value
        game = None
        for row, column in cells:
            response = self.move(player_id, row, column, value)
            assert response.status_code == 200, (row, column, value, response.get_data(as_text=True))
            game = response.get_json()["game"]
            value = -value
        return game

    def ai_move(self, player_id):
        return self.client.get(f"/api/ai-move?player-id={player_id}")

    def train(self, amount):
        return self.client.post("/api/ai-train", json={"amount": amount})




def error_code(response):
    body = response.get_json(silent=True) or {}
    error = body.get("error")
    if isinstance(error, dict):
        return error.get("code")
    return None


# Reusable move sequences (X = 1 always starts).
X_WINS_ROW0 = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]
O_WINS_ROW1 = [(0, 0), (1, 0), (0, 1), (1, 1), (2, 2), (1, 2)]
DRAW = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 0), (1, 2), (2, 1), (2, 0), (2, 2)]
# Full board where X's 9th move completes the main diagonal.
X_WINS_ON_LAST_CELL = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 1), (2, 0), (2, 2)]

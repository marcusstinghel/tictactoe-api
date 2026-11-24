from typing import Optional


class Player:
    def __init__(self, id: Optional[int], first_name: str, last_name: str, nickname: str,
                 victories: int = 0, defeats: int = 0, draws: int = 0):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.nickname = nickname
        self.victories = victories
        self.defeats = defeats
        self.draws = draws

    def record_result(self, winner: int) -> None:
        """winner: 1 means the player (X) won, -1 means the AI (O) won, 0 is a draw."""
        if winner == 1:
            self.victories += 1
        elif winner == -1:
            self.defeats += 1
        else:
            self.draws += 1

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'nickname': self.nickname,
            'victories': self.victories,
            'defeats': self.defeats,
            'draws': self.draws,
        }

    def __repr__(self):
        return (f"Player(id={self.id}, nickname={self.nickname}, victories={self.victories}, "
                f"defeats={self.defeats}, draws={self.draws})")

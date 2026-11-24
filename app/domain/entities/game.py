from typing import List, Literal, Optional

from app.domain.entities import Board, Movements
from app.domain.exceptions import CellOccupied, GameFinished, InvalidMovement, NotYourTurn

X = 1
O = -1
LINES = (
    ((0, 0), (0, 1), (0, 2)),
    ((1, 0), (1, 1), (1, 2)),
    ((2, 0), (2, 1), (2, 2)),
    ((0, 0), (1, 0), (2, 0)),
    ((0, 1), (1, 1), (2, 1)),
    ((0, 2), (1, 2), (2, 2)),
    ((0, 0), (1, 1), (2, 2)),
    ((0, 2), (1, 1), (2, 0)),
)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class Game:
    """A tic-tac-toe match. X (1) always starts; the human is X and the AI is O (-1)."""

    def __init__(
            self,
            id: Optional[int],
            state: Literal['in_progress', 'finished'],
            player_id: int,
            movements: Movements,
            winner: Literal[-1, 0, 1],
            board: Board,
    ):
        self.id = id
        self.state = state
        self.player_id = player_id
        self.movements = [dict(m) for m in movements]
        self.winner = winner
        self.board = [list(row) for row in board]

    @classmethod
    def new(cls, player_id: int) -> "Game":
        return cls(id=None, state='in_progress', player_id=player_id, movements=[], winner=0,
                   board=[[0, 0, 0], [0, 0, 0], [0, 0, 0]])

    @property
    def is_finished(self) -> bool:
        return self.state == 'finished'

    @property
    def next_mark(self) -> int:
        return X if len(self.movements) % 2 == 0 else O

    def flat_board(self) -> List[int]:
        return [cell for row in self.board for cell in row]

    def play(self, row, column, mark) -> None:
        if self.is_finished:
            raise GameFinished()
        if not (_is_int(row) and _is_int(column) and 0 <= row <= 2 and 0 <= column <= 2):
            raise InvalidMovement()
        if not (_is_int(mark) and mark in (X, O)):
            raise InvalidMovement()
        if mark != self.next_mark:
            raise NotYourTurn()
        if self.board[row][column] != 0:
            raise CellOccupied()

        self.board[row][column] = mark
        self.movements.append({'row': row, 'column': column, 'value': mark})
        if self._has_won(mark):
            self.state = 'finished'
            self.winner = mark
        elif all(cell != 0 for cell in self.flat_board()):
            self.state = 'finished'
            self.winner = 0

    def _has_won(self, mark: int) -> bool:
        return any(all(self.board[r][c] == mark for r, c in line) for line in LINES)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'player_id': self.player_id,
            'board': [list(row) for row in self.board],
            'state': self.state,
            'winner': self.winner,
            'movements': [dict(m) for m in self.movements],
        }

    def __repr__(self):
        return (f"Game(id={self.id}, board={self.board}, state={self.state}, player_id={self.player_id}, "
                f"movements={self.movements}, winner={self.winner})")

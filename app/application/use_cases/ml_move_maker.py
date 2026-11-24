from typing import Tuple

from app.application.use_cases.helpers import current_game, require_player
from app.domain.ml import MLMovementInterface
from app.domain.repositories import GameRepositoryInterface, PlayerRepositoryInterface


class MLMoveMaker:
    def __init__(self, game_repository: GameRepositoryInterface, player_repository: PlayerRepositoryInterface,
                 ml_movement: MLMovementInterface):
        self._game_repository = game_repository
        self._player_repository = player_repository
        self._ml_movement = ml_movement

    def make_move(self, player_id: int) -> Tuple[int, int]:
        """Suggests a cell for the side to move. Read-only: the move is not applied."""
        require_player(self._player_repository, player_id)
        game = current_game(self._game_repository, player_id)
        mark = game.next_mark
        board = [cell * mark for cell in game.flat_board()]
        position = self._ml_movement.make_move(board=board)
        if not 0 <= position <= 8 or board[position] != 0:
            position = board.index(0)
        return divmod(position, 3)

from typing import List, Tuple

from app.domain.entities import Game


def build_training_samples(games: List[Game]) -> List[Tuple[List[int], int]]:
    """Turns finished games into (board, target) pairs.

    Only moves worth imitating are kept: every move of the winner, or every move of both sides
    in a draw. The board is the one before the move, seen by the mover (own marks are 1), and the
    target is the chosen cell index (row * 3 + column).
    """
    samples: List[Tuple[List[int], int]] = []
    for game in games:
        if game.state != 'finished':
            continue
        board = [0] * 9
        for movement in game.movements:
            mark = movement['value']
            cell = movement['row'] * 3 + movement['column']
            if game.winner == 0 or mark == game.winner:
                samples.append(([value * mark for value in board], cell))
            board[cell] = mark
    return samples

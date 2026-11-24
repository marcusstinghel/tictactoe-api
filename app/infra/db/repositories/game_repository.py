from typing import List, Optional

from sqlalchemy import select

from app.domain.entities import Game
from app.domain.exceptions import GameNotFound
from app.domain.repositories import GameRepositoryInterface
from app.infra.db.entities import Game as GameRow


def _to_entity(row: GameRow) -> Game:
    return Game(
        id=row.id,
        state=row.state,
        player_id=row.player_id,
        movements=row.movements,
        winner=row.winner,
        board=row.board,
    )


class GameRepository(GameRepositoryInterface):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def create_game(self, game: Game) -> Game:
        row = GameRow(
            board=[list(r) for r in game.board],
            state=game.state,
            player_id=game.player_id,
            movements=[dict(m) for m in game.movements],
            winner=game.winner,
        )
        with self._session_factory.begin() as session:
            session.add(row)
            session.flush()
            return _to_entity(row)

    def get_in_progress_game(self, player_id: int) -> Optional[Game]:
        statement = (select(GameRow)
                     .where(GameRow.player_id == player_id, GameRow.state == 'in_progress')
                     .order_by(GameRow.id.desc())
                     .limit(1))
        return self._first(statement)

    def get_latest_game(self, player_id: int) -> Optional[Game]:
        statement = (select(GameRow)
                     .where(GameRow.player_id == player_id)
                     .order_by(GameRow.id.desc())
                     .limit(1))
        return self._first(statement)

    def get_finished_games(self, limit: int) -> List[Game]:
        statement = (select(GameRow)
                     .where(GameRow.state == 'finished')
                     .order_by(GameRow.id.desc())
                     .limit(limit))
        with self._session_factory() as session:
            return [_to_entity(row) for row in session.scalars(statement)]

    def update_game(self, game: Game) -> Game:
        with self._session_factory.begin() as session:
            row = session.get(GameRow, game.id)
            if row is None:
                raise GameNotFound()
            # JSON columns need brand new lists: in-place mutation is not detected.
            row.board = [list(r) for r in game.board]
            row.movements = [dict(m) for m in game.movements]
            row.state = game.state
            row.winner = game.winner
            session.flush()
            return _to_entity(row)

    def _first(self, statement) -> Optional[Game]:
        with self._session_factory() as session:
            row = session.scalars(statement).first()
            return _to_entity(row) if row is not None else None

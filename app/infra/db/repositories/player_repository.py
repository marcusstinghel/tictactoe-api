from typing import Optional

from sqlalchemy.exc import IntegrityError

from app.domain.entities import Player
from app.domain.exceptions import NicknameTaken, PlayerNotFound
from app.domain.repositories import PlayerRepositoryInterface
from app.infra.db.entities import Player as PlayerRow


def _to_entity(row: PlayerRow) -> Player:
    return Player(
        id=row.id,
        first_name=row.first_name,
        last_name=row.last_name,
        nickname=row.nickname,
        victories=row.victories,
        defeats=row.defeats,
        draws=row.draws,
    )


class PlayerRepository(PlayerRepositoryInterface):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def create_player(self, first_name: str, last_name: str, nickname: str) -> Player:
        row = PlayerRow(first_name=first_name, last_name=last_name, nickname=nickname,
                        victories=0, defeats=0, draws=0)
        try:
            with self._session_factory.begin() as session:
                session.add(row)
                session.flush()
                return _to_entity(row)
        except IntegrityError:
            raise NicknameTaken()

    def get_player(self, id: int) -> Optional[Player]:
        with self._session_factory() as session:
            row = session.get(PlayerRow, id)
            return _to_entity(row) if row is not None else None

    def update_player(self, player: Player) -> Player:
        with self._session_factory.begin() as session:
            row = session.get(PlayerRow, player.id)
            if row is None:
                raise PlayerNotFound()
            row.first_name = player.first_name
            row.last_name = player.last_name
            row.nickname = player.nickname
            row.victories = player.victories
            row.defeats = player.defeats
            row.draws = player.draws
            session.flush()
            return _to_entity(row)

from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.infra.db.entities import Base


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True, index=True)
    board = Column(JSON, nullable=False)
    state = Column(String, nullable=False)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    movements = Column(JSON, nullable=False)
    winner = Column(Integer, nullable=False)

    player = relationship('Player', back_populates='games')

    def __repr__(self):
        return f"<Game(id={self.id}, state={self.state}, player_id={self.player_id}, winner={self.winner})>"

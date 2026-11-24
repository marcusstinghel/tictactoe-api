from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.infra.db.entities import Base


class Player(Base):
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    nickname = Column(String, unique=True, nullable=False)
    victories = Column(Integer, nullable=False, default=0)
    defeats = Column(Integer, nullable=False, default=0)
    draws = Column(Integer, nullable=False, default=0)

    games = relationship('Game', back_populates='player')

    def __repr__(self):
        return f"<Player(id={self.id}, nickname={self.nickname})>"

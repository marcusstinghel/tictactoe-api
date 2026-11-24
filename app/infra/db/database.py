from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infra.db.entities import Base


class Database:
    """One engine and one session factory per application."""

    def __init__(self, url: str):
        self.engine = create_engine(url)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)

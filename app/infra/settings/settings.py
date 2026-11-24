import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from dotenv import dotenv_values

DEFAULT_DB_CONNECTION_STRING = "sqlite:///tictactoe.db"
DEFAULT_ML_MODEL_PATH = "models/tictactoe_model.pth"


@dataclass(frozen=True)
class Settings:
    db_connection_string: str
    ml_model_path: str


def load_settings(overrides: Optional[Mapping] = None) -> Settings:
    """Precedence: overrides > process environment > .env in the current directory > defaults."""
    overrides = overrides or {}
    dotenv = dotenv_values(Path.cwd() / ".env")

    def pick(name: str, default: str) -> str:
        for source in (overrides, os.environ, dotenv):
            value = source.get(name)
            if value:
                return str(value)
        return default

    return Settings(
        db_connection_string=pick("DB_CONNECTION_STRING", DEFAULT_DB_CONNECTION_STRING),
        ml_model_path=pick("ML_MODEL_PATH", DEFAULT_ML_MODEL_PATH),
    )

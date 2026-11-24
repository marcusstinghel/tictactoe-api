"""Composition root: the only module that wires infrastructure into the use cases."""
from dataclasses import dataclass
from typing import Mapping, Optional

from app.application.use_cases import (
    GameMoveMaker,
    GameStarter,
    MLMoveMaker,
    MLTrainer,
    PlayerCreator,
    PlayerFinder,
)
from app.infra.ai.learning import AILearning
from app.infra.ai.movement import AIMovement
from app.infra.db.database import Database
from app.infra.db.repositories import GameRepository, PlayerRepository
from app.infra.settings.settings import Settings, load_settings


@dataclass
class Container:
    settings: Settings
    player_creator: PlayerCreator
    player_finder: PlayerFinder
    game_starter: GameStarter
    game_move_maker: GameMoveMaker
    ml_trainer: MLTrainer
    ml_move_maker: MLMoveMaker


def build_container(config: Optional[Mapping] = None) -> Container:
    settings = load_settings(config)
    database = Database(settings.db_connection_string)
    database.create_tables()

    player_repository = PlayerRepository(database.session_factory)
    game_repository = GameRepository(database.session_factory)
    ml_learning = AILearning(settings.ml_model_path)
    ml_movement = AIMovement(settings.ml_model_path)

    return Container(
        settings=settings,
        player_creator=PlayerCreator(player_repository),
        player_finder=PlayerFinder(player_repository),
        game_starter=GameStarter(game_repository, player_repository),
        game_move_maker=GameMoveMaker(game_repository, player_repository),
        ml_trainer=MLTrainer(game_repository, ml_learning),
        ml_move_maker=MLMoveMaker(game_repository, player_repository, ml_movement),
    )

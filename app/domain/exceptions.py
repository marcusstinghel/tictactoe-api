"""Domain errors. Each one carries a stable ``code``; the interface layer maps codes to HTTP."""
from typing import Optional


class DomainError(Exception):
    code = "domain_error"
    default_message = "Domain error"

    def __init__(self, message: Optional[str] = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidMovement(DomainError):
    code = "invalid_movement"
    default_message = "Row and column must be integers between 0 and 2 and value must be 1 or -1"


class PlayerNotFound(DomainError):
    code = "player_not_found"
    default_message = "Player not found"


class GameNotFound(DomainError):
    code = "game_not_found"
    default_message = "Game not found"


class NotYourTurn(DomainError):
    code = "not_your_turn"
    default_message = "It is not this mark's turn"


class CellOccupied(DomainError):
    code = "cell_occupied"
    default_message = "The cell is already occupied"


class GameFinished(DomainError):
    code = "game_finished"
    default_message = "The game is already finished"


class GameAlreadyInProgress(DomainError):
    code = "game_already_in_progress"
    default_message = "The player already has a game in progress"


class NicknameTaken(DomainError):
    code = "nickname_taken"
    default_message = "Nickname already in use"


class ModelNotTrained(DomainError):
    code = "model_not_trained"
    default_message = "The AI model has not been trained yet"


class NoTrainingData(DomainError):
    code = "no_training_data"
    default_message = "There are no finished games to train on"

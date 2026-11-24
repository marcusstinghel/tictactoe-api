from app.domain.entities import Game, Player
from app.domain.exceptions import GameFinished, GameNotFound, PlayerNotFound
from app.domain.repositories import GameRepositoryInterface, PlayerRepositoryInterface


def require_player(player_repository: PlayerRepositoryInterface, player_id: int) -> Player:
    player = player_repository.get_player(id=player_id)
    if player is None:
        raise PlayerNotFound()
    return player


def current_game(game_repository: GameRepositoryInterface, player_id: int) -> Game:
    """The player's game in progress. Without one: GameFinished if they played before, else GameNotFound."""
    game = game_repository.get_in_progress_game(player_id=player_id)
    if game is not None:
        return game
    if game_repository.get_latest_game(player_id=player_id) is not None:
        raise GameFinished()
    raise GameNotFound()

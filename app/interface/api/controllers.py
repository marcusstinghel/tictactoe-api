"""HTTP controllers: validate the request envelope and call the use cases."""
from flask import Blueprint, current_app, jsonify, request

from app.interface.api.errors import ValidationError

api = Blueprint("api", __name__, url_prefix="/api")


def _container():
    return current_app.extensions["container"]


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _json_object() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")
    return body


def _int_field(body: dict, name: str) -> int:
    value = body.get(name)
    if not _is_int(value):
        raise ValidationError(f"'{name}' must be an integer")
    return value


def _text_field(body: dict, name: str) -> str:
    value = body.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"'{name}' must be a non-empty string")
    return value


@api.get("/health")
def health():
    return jsonify({"status": "ok", "name": "tictactoe-api"})


@api.post("/register")
def register():
    body = _json_object()
    player = _container().player_creator.create(
        first_name=_text_field(body, "first_name"),
        last_name=_text_field(body, "last_name"),
        nickname=_text_field(body, "nickname"),
    )
    return jsonify(player.to_dict()), 201


@api.get("/players/<int:player_id>")
def get_player(player_id: int):
    return jsonify(_container().player_finder.find(player_id).to_dict())


@api.post("/start")
def start():
    body = _json_object()
    game = _container().game_starter.start(_int_field(body, "player_id"))
    return jsonify(game.to_dict()), 201


@api.post("/move")
def move():
    body = _json_object()
    player_id = _int_field(body, "player_id")
    movement = body.get("movement")
    if not isinstance(movement, dict) or not {"row", "column", "value"} <= movement.keys():
        raise ValidationError("'movement' must be an object with row, column and value")
    game = _container().game_move_maker.make_move(
        player_id=player_id, row=movement["row"], column=movement["column"], value=movement["value"])
    return jsonify({"message": "Move registered", "game": game.to_dict()})


@api.get("/ai-move")
def ai_move():
    raw = request.args.get("player-id", "")
    if not raw.isascii() or not raw.isdigit():
        raise ValidationError("'player-id' query parameter must be an integer")
    row, column = _container().ml_move_maker.make_move(int(raw))
    return jsonify({"row": row, "column": column, "position": row * 3 + column})


@api.post("/ai-train")
def ai_train():
    body = _json_object()
    amount = _int_field(body, "amount")
    if amount <= 0:
        raise ValidationError("'amount' must be greater than zero")
    samples = _container().ml_trainer.train(amount)
    return jsonify({"message": "Training finished", "samples": samples})

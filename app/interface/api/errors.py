import logging

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.domain import exceptions as domain

logger = logging.getLogger(__name__)

STATUS_BY_ERROR = {
    domain.InvalidMovement: 400,
    domain.PlayerNotFound: 404,
    domain.GameNotFound: 404,
    domain.NotYourTurn: 409,
    domain.CellOccupied: 409,
    domain.GameFinished: 409,
    domain.GameAlreadyInProgress: 409,
    domain.NicknameTaken: 409,
    domain.ModelNotTrained: 409,
    domain.NoTrainingData: 409,
}


class ValidationError(Exception):
    """The request envelope is malformed (missing field, wrong type, bad query)."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def error_response(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def handle_validation(error: ValidationError):
        return error_response("validation_error", error.message, 400)

    @app.errorhandler(domain.DomainError)
    def handle_domain(error: domain.DomainError):
        return error_response(error.code, error.message, STATUS_BY_ERROR.get(type(error), 400))

    @app.errorhandler(HTTPException)
    def handle_http(error: HTTPException):
        code = (error.name or "http_error").lower().replace(" ", "_")
        return error_response(code, error.description or error.name, error.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        logger.exception("Unhandled error")
        return error_response("internal_error", "Internal server error", 500)

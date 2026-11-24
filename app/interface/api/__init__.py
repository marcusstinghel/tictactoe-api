from typing import Mapping, Optional

from flask import Flask

from app.container import build_container
from app.interface.api.controllers import api
from app.interface.api.errors import register_error_handlers


def create_app(config: Optional[Mapping] = None) -> Flask:
    app = Flask(__name__)
    if config:
        app.config.update(config)
    app.extensions["container"] = build_container(config)
    app.register_blueprint(api)
    register_error_handlers(app)
    return app

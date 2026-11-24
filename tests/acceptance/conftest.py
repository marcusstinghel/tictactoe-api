"""Shared fixtures for the acceptance suite.

Contract (see docs/ACCEPTANCE_CRITERIA.md):
- ``create_app(config: dict | None = None)`` lives in ``app.interface.api``.
- ``config`` keys mirror the environment variables: ``DB_CONNECTION_STRING``
  and ``ML_MODEL_PATH``. Values passed in ``config`` win over the environment.
- ``create_app`` creates the database tables itself.

Every test runs in an empty temporary directory, with a temporary SQLite file
and a temporary model path. Nothing from the author's machine is used and no
network access is needed.
"""
import pytest

from .support import Api

ENV_VARS = ("DB_CONNECTION_STRING", "ML_MODEL_PATH", "ML_PATH_FILE_PATH")


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def config(isolated):
    return {
        "TESTING": True,
        "DB_CONNECTION_STRING": "sqlite:///" + (isolated / "acceptance.db").as_posix(),
        "ML_MODEL_PATH": str(isolated / "model" / "acceptance_model.pth"),
    }


@pytest.fixture
def app(config):
    from app.interface.api import create_app

    return create_app(config)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def api(client):
    return Api(client)

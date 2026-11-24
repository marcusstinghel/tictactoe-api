"""Repository hygiene, rename and reproducibility (criteria AC-01 to AC-09, AC-30, AC-31)."""
import re
import shutil
import subprocess
import tomllib

import pytest

from .support import ROOT

# Files that legitimately mention the old names (they document the rename).
EXEMPT_PREFIXES = ("docs/", "tests/acceptance/")

OLD_NAMES = re.compile(r"tictactoe_python_api|tictactoe_api|tic tac toe python api", re.IGNORECASE)
# Absolute, machine-specific paths such as C:/Users/<name>/ or /home/<name>/.
ABSOLUTE_USER_PATH = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+|/home/[A-Za-z]|/Users/[A-Za-z]")


def _git(*args):
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("needs a git checkout")
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def _tracked_text_files():
    for rel in _git("ls-files").splitlines():
        if rel.startswith(EXEMPT_PREFIXES):
            continue
        path = ROOT / rel
        try:
            yield rel, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue


def test_dotenv_is_not_versioned_and_is_ignored():
    assert _git("ls-files", ".env").strip() == ""
    assert _git("check-ignore", ".env").strip() == ".env"


def test_env_example_documents_every_setting():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DB_CONNECTION_STRING=" in example
    assert "ML_MODEL_PATH=" in example
    assert not ABSOLUTE_USER_PATH.search(example)


def test_generated_artifacts_are_not_versioned():
    tracked = _git("ls-files").splitlines()
    assert [f for f in tracked if f.endswith((".pth", ".db", ".sqlite", ".sqlite3", ".pyc"))] == []


def test_old_project_name_is_gone():
    offenders = [rel for rel, text in _tracked_text_files() if OLD_NAMES.search(text) or OLD_NAMES.search(rel)]
    assert offenders == []


def test_no_machine_specific_absolute_paths():
    offenders = [rel for rel, text in _tracked_text_files() if ABSOLUTE_USER_PATH.search(text)]
    assert offenders == []


def test_project_metadata_uses_new_name():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "tictactoe-api"
    assert data["project"]["requires-python"].startswith(">=3.")


def test_readme_title_and_from_scratch_instructions():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.splitlines()[0].strip() == "# tictactoe-api"
    for needle in (".env.example", "requirements-dev.txt", "pytest", "/api/health", "/api/ai-train"):
        assert needle in readme, needle
    assert "Copiar código" not in readme


def test_requirements_are_runtime_only_and_installable_on_313():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    names = {re.split(r"[=<>!~\[ ;]", line.strip(), maxsplit=1)[0]
             for line in runtime.splitlines() if line.strip() and not line.startswith("#")}
    assert {"flask", "sqlalchemy", "torch", "python-dotenv"} <= names
    assert not names & {"pytest", "torchvision", "torchaudio", "aiosqlite", "pillow"}
    assert "torch==2.5.1" not in runtime  # no Windows wheel for Python 3.13
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
    assert "pytest" in dev


def test_ci_workflow_runs_pytest():
    workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows, "expected a GitHub Actions workflow"
    text = "\n".join(w.read_text(encoding="utf-8") for w in workflows)
    assert "pytest" in text
    assert "3.13" in text
    assert "download.pytorch.org/whl/cpu" in text  # CPU wheel keeps CI fast


def test_entrypoint_does_not_enable_debugger():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    # Werkzeug debugger bound to 0.0.0.0 allows remote code execution.
    assert "debug=True" not in source


def test_create_app_does_not_need_dotenv_or_author_files(isolated):
    """With no .env and no config, the app still boots using local defaults."""
    from app.interface.api import create_app

    app = create_app({"TESTING": True})
    response = app.test_client().get("/api/health")
    assert response.status_code == 200

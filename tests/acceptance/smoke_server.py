"""Boot the real server (python main.py) and play a full game over HTTP on 127.0.0.1.

Not collected by pytest (no ``test_`` prefix). Criterion AC-32:
    python tests/acceptance/smoke_server.py
Runs in a fresh temporary directory, so no .env, database or model of the machine is used.
Exit code 0 = success.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _call(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def main():
    port = _free_port()
    base = f"http://127.0.0.1:{port}/api"
    with tempfile.TemporaryDirectory() as workdir:
        env = {k: v for k, v in os.environ.items()
               if k not in ("DB_CONNECTION_STRING", "ML_MODEL_PATH", "ML_PATH_FILE_PATH")}
        env.update({"PORT": str(port), "PYTHONPATH": str(ROOT)})
        server = subprocess.Popen([sys.executable, str(ROOT / "main.py")], cwd=workdir, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while True:
                if server.poll() is not None:
                    output = server.stdout.read().decode(errors="replace")[-2000:]
                    raise SystemExit(f"server exited with code {server.returncode}: {output}")
                try:
                    status, body = _call(base, "GET", "/health")
                    break
                except (urllib.error.URLError, ConnectionError):
                    if time.monotonic() > deadline:
                        raise SystemExit("server did not answer /api/health within 60s")
                    time.sleep(0.5)
            assert (status, body) == (200, {"status": "ok", "name": "tictactoe-api"}), (status, body)

            status, player = _call(base, "POST", "/register",
                                   {"first_name": "Smoke", "last_name": "Test", "nickname": "smoke"})
            assert status == 201, (status, player)
            pid = player["id"]
            status, game = _call(base, "POST", "/start", {"player_id": pid})
            assert status == 201, (status, game)

            value = 1
            for row, column in [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]:
                status, body = _call(base, "POST", "/move",
                                     {"player_id": pid, "movement": {"row": row, "column": column, "value": value}})
                assert status == 200, (status, body)
                value = -value
            assert (body["game"]["state"], body["game"]["winner"]) == ("finished", 1), body

            status, body = _call(base, "POST", "/ai-train", {"amount": 10})
            assert status == 200, (status, body)
            _call(base, "POST", "/start", {"player_id": pid})
            _call(base, "POST", "/move", {"player_id": pid, "movement": {"row": 1, "column": 1, "value": 1}})
            status, body = _call(base, "GET", f"/ai-move?player-id={pid}")
            assert status == 200 and (body["row"], body["column"]) != (1, 1), (status, body)

            status, body = _call(base, "GET", f"/players/{pid}")
            assert status == 200 and body["victories"] == 1, (status, body)
            print("SMOKE OK")
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    main()

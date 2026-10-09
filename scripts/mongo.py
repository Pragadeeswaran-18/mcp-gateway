"""Manage a local MongoDB and open a shell on the project database.

  uv run python scripts/mongo.py start     # start mongod if it is not running
  uv run python scripts/mongo.py stop
  uv run python scripts/mongo.py status
  uv run python scripts/mongo.py shell     # start if needed, then open mongosh on MONGO_DB
  uv run python scripts/mongo.py shell --eval "db.rules.find()"   # extra args go to mongosh

Binaries are looked up under MONGO_HOME (default %LOCALAPPDATA%\\mongodb on Windows,
~/.local/share/mongodb elsewhere): server/**/bin/mongod and tools/node_modules/.bin/mongosh,
falling back to PATH. Data and logs live in MONGO_HOME/data and MONGO_HOME/logs.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

IS_WINDOWS = os.name == "nt"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "policy_gateway")


def mongo_home() -> Path:
    if "MONGO_HOME" in os.environ:
        return Path(os.environ["MONGO_HOME"])
    if IS_WINDOWS:
        return Path(os.environ["LOCALAPPDATA"]) / "mongodb"
    return Path.home() / ".local" / "share" / "mongodb"


def find_mongod() -> str:
    exe = "mongod.exe" if IS_WINDOWS else "mongod"
    found = next((mongo_home() / "server").glob(f"**/bin/{exe}"), None)
    path = str(found) if found else shutil.which("mongod")
    if not path:
        sys.exit(f"mongod not found under {mongo_home() / 'server'} or on PATH")
    return path


def find_mongosh() -> str:
    name = "mongosh.cmd" if IS_WINDOWS else "mongosh"
    local = mongo_home() / "tools" / "node_modules" / ".bin" / name
    path = str(local) if local.exists() else shutil.which("mongosh")
    if not path:
        sys.exit(f"mongosh not found at {local} or on PATH")
    return path


def host_port() -> tuple[str, int]:
    parts = urlsplit(MONGO_URL)
    return parts.hostname or "localhost", parts.port or 27017


def is_running() -> bool:
    try:
        with socket.create_connection(host_port(), timeout=0.5):
            return True
    except OSError:
        return False


def start() -> None:
    if is_running():
        print(f"MongoDB already running at {MONGO_URL}")
        return
    home = mongo_home()
    (home / "data").mkdir(parents=True, exist_ok=True)
    (home / "logs").mkdir(parents=True, exist_ok=True)
    cmd = [
        find_mongod(),
        "--dbpath", str(home / "data"),
        "--logpath", str(home / "logs" / "mongod.log"),
        "--bind_ip", "127.0.0.1",
        "--port", str(host_port()[1]),
    ]  # fmt: skip
    flags = 0
    if IS_WINDOWS:
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        start_new_session=not IS_WINDOWS,
    )
    for _ in range(100):
        if is_running():
            print(f"MongoDB started at {MONGO_URL} (log: {home / 'logs' / 'mongod.log'})")
            return
        time.sleep(0.2)
    sys.exit(f"mongod did not start; see {home / 'logs' / 'mongod.log'}")


def stop() -> None:
    if not is_running():
        print("MongoDB is not running")
        return
    admin_url = urlunsplit(urlsplit(MONGO_URL)._replace(path="/admin"))
    subprocess.call([find_mongosh(), admin_url, "--quiet", "--eval", "db.shutdownServer()"])
    print("shutdown requested")


def shell(extra: list[str]) -> int:
    start()
    url = urlunsplit(urlsplit(MONGO_URL)._replace(path=f"/{MONGO_DB}"))
    return subprocess.call([find_mongosh(), url, *extra])


def main() -> int:
    cmd, *rest = sys.argv[1:] or ["shell"]
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        print("running" if is_running() else "stopped")
    elif cmd == "shell":
        return shell(rest)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

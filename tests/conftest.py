"""Fixtures: in-process upstream, subprocess gateway, and per-user clients."""

import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from fastmcp import Client
from mint_jwt import mint

from upstream import server as upstream_server

ROOT = Path(__file__).resolve().parent.parent
JWT_SECRET = "test-secret-not-for-production-use-0123456789"
USER_A_PHONE = "999999999"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float, proc: subprocess.Popen | None = None) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.1)
    return False


@pytest.fixture(scope="session")
def upstream_url() -> Iterator[str]:
    """Run the real upstream server in a background thread of this process, so tests can
    inspect `upstream.server.received` directly."""
    port = _free_port()
    config = uvicorn.Config(
        upstream_server.mcp.http_app(), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # not on the main thread
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    assert _wait_for_port(port, 10), "upstream failed to start"
    yield f"http://127.0.0.1:{port}/mcp"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def reset_upstream() -> None:
    upstream_server.received.clear()


@pytest.fixture
def received() -> list:
    """Calls the upstream actually received, as (tool, arguments) tuples."""
    return upstream_server.received


@pytest.fixture(scope="session")
def audit_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("audit") / "audit.db"


@pytest.fixture(scope="session")
def gateway_url(upstream_url: str, audit_db: Path) -> Iterator[str]:
    """Start the gateway as a subprocess pointed at the test upstream.

    Does not fail when the gateway cannot start (it is a stub today); tests then fail on
    their first client call instead.
    """
    port = _free_port()
    env = {
        **os.environ,
        "GATEWAY_JWT_SECRET": JWT_SECRET,
        "USER_A_PHONE": USER_A_PHONE,
        "UPSTREAM_URL": upstream_url,
        "GATEWAY_PORT": str(port),
        "GATEWAY_AUDIT_DB": str(audit_db),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "gateway.server"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_port(port, 15, proc)
    yield f"http://127.0.0.1:{port}/mcp"
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def token_for(user: str, secret: str = JWT_SECRET) -> str:
    return mint(user, secret)


@pytest.fixture
def alice(gateway_url: str) -> Client:
    """Unconnected client; tests enter it with `async with` so connect errors fail the test."""
    return Client(gateway_url, auth=token_for("alice"))


@pytest.fixture
def bob(gateway_url: str) -> Client:
    """Unconnected client; see `alice`."""
    return Client(gateway_url, auth=token_for("bob"))


@pytest.fixture
def audit_rows(audit_db: Path):
    """Callable returning all audit rows as dicts (empty if the table does not exist)."""

    def read() -> list[dict]:
        if not audit_db.exists():
            return []
        conn = sqlite3.connect(audit_db)
        conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in conn.execute("SELECT * FROM audit_events ORDER BY id")]
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

    return read

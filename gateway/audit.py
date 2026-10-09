"""Append-only SQLite audit log tying every decision to a human and an agent."""

from typing import Any

from gateway.session import Session

# Expected table `audit_events` (path from env GATEWAY_AUDIT_DB, default "audit.db"):
#   id INTEGER PRIMARY KEY, ts TEXT, human TEXT, agent TEXT, task_id TEXT,
#   tool TEXT, decision TEXT, rule TEXT, reason TEXT, arguments TEXT (JSON, redacted)
# tests/test_scenarios.py reads this table; change both together.


def init_db() -> None:
    """Create the `audit_events` table if missing and install triggers that make it
    append-only (abort UPDATE and DELETE)."""
    raise NotImplementedError


def write_event(
    session: Session,
    tool: str,
    decision: str,
    rule: str,
    reason: str = "",
    arguments: dict[str, Any] | None = None,
) -> None:
    """Insert one row into `audit_events` for this decision.

    Must: record human, agent and task_id from the session, never store resolved secret
    values, and never fail in a way that lets a call proceed unaudited.
    """
    raise NotImplementedError

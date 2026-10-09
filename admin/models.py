"""Pydantic documents stored in MongoDB and exchanged over the admin API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Pin(BaseModel):
    """An argument forced to a value (or "ref:NAME" secret) and hidden from the model."""

    value: str
    on_conflict: Literal["reject", "override"] = "reject"


class Constraint(BaseModel):
    """Constraint on an argument's value."""

    reject_pattern: str | None = None  # regex; a match rejects the call


class ToolRule(BaseModel):
    """Per-tool policy. A user in no list falls back to the global default (deny)."""

    tool: str
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    require_approval: list[str] = Field(default_factory=list)
    pins: dict[str, Pin] = Field(default_factory=dict)
    constraints: dict[str, Constraint] = Field(default_factory=dict)


class User(BaseModel):
    """A human who may use the gateway."""

    username: str
    active: bool = True
    agent_ids: list[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    """A require_approval call waiting for an admin."""

    id: str
    human: str
    agent: str
    task_id: str
    tool: str
    arguments: dict = Field(default_factory=dict)  # redacted
    status: Literal["pending", "approved", "denied"] = "pending"
    created_at: datetime
    resolved_by: str | None = None


class AuditEvent(BaseModel):
    """One gateway decision, tied to a human and an agent."""

    ts: datetime
    human: str
    agent: str
    task_id: str
    tool: str
    decision: str
    rule: str
    reason: str = ""
    arguments: dict = Field(default_factory=dict)  # redacted

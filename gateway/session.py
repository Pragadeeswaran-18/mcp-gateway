"""Per-connection identity established at initialize time."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Session:
    """Who is acting: a human, via a specific agent, on a specific task."""

    human: str
    agent: str
    task_id: str
    started_at: datetime

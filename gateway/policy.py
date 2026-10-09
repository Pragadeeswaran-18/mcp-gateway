"""Policy evaluation against rules loaded from policies/rules.yaml."""

from dataclasses import dataclass, field
from typing import Any, Literal

from gateway.session import Session


@dataclass(frozen=True)
class Decision:
    """Outcome of evaluating one tool call."""

    action: Literal["allow", "deny", "require_approval"]
    rule: str
    reason: str = ""
    # Arguments after pinning/overrides; what is actually forwarded upstream.
    arguments: dict[str, Any] = field(default_factory=dict)


def evaluate(session: Session, tool: str, args: dict[str, Any]) -> Decision:
    """Decide what happens to a call to `tool` with `args` for `session`.

    Must: apply the default action, per-tool per-user allow/deny/require_approval,
    reject calls that supply a pinned argument when on_conflict is "reject", inject pinned
    values (resolved via gateway.secrets), and enforce argument constraints (e.g. regex
    rejecting 9+ digit sequences). The returned Decision names the rule that decided it.
    """
    raise NotImplementedError

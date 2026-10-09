"""CRUD for per-tool rules."""

from fastapi import APIRouter

from common.models import ToolRule

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
async def list_rules() -> list[ToolRule]:
    """List all rules."""
    raise NotImplementedError


@router.put("/{tool}")
async def put_rule(tool: str, rule: ToolRule) -> ToolRule:
    """Create or replace the rule for `tool`. Must validate regexes and return 422 when the
    path and body tool names differ."""
    raise NotImplementedError


@router.delete("/{tool}", status_code=204)
async def delete_rule(tool: str) -> None:
    """Delete a rule; 404 if missing."""
    raise NotImplementedError

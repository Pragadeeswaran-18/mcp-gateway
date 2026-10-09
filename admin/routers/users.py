"""CRUD for users."""

from fastapi import APIRouter

from admin.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users() -> list[User]:
    """List all users."""
    raise NotImplementedError


@router.put("/{username}")
async def put_user(username: str, user: User) -> User:
    """Create or replace a user."""
    raise NotImplementedError


@router.delete("/{username}", status_code=204)
async def delete_user(username: str) -> None:
    """Delete a user; 404 if missing."""
    raise NotImplementedError

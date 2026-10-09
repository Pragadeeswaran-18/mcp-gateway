"""CRUD for users."""

from typing import Annotated

from fastapi import APIRouter, Depends

from admin.deps import get_store
from common.models import User
from common.store.base import PolicyStore

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(store: Annotated[PolicyStore, Depends(get_store)]) -> list[User]:
    """List all users of the request's tenant (resolved from the subdomain), by username."""
    return await store.list_users()


@router.put("/{username}")
async def put_user(username: str, user: User) -> User:
    """Create or replace a user."""
    raise NotImplementedError


@router.delete("/{username}", status_code=204)
async def delete_user(username: str) -> None:
    """Delete a user; 404 if missing."""
    raise NotImplementedError

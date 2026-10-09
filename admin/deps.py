"""FastAPI dependencies shared by the admin routers."""

from fastapi import Request

from common.store.base import PolicyStore


def get_store(request: Request) -> PolicyStore:
    """The PolicyStore created in create_app."""
    return request.app.state.store

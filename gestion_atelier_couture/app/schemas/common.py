"""Schémas partagés : pagination générique Page[T]."""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Réponse paginée standard : {"items": [...], "total": 42, "limit": 20, "offset": 0}."""

    items: list[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    detail: str

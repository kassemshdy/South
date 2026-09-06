"""Shared response shapes."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """The single error envelope returned by every failing endpoint."""

    error: ErrorDetail


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


class MessageResponse(BaseModel):
    message: str


class StatsResponse(BaseModel):
    total_businesses: int = Field(description="All businesses regardless of status")
    pending_businesses: int
    approved_businesses: int
    rejected_businesses: int
    suspended_businesses: int
    draft_businesses: int
    total_users: int
    total_admins: int
    total_items: int
    total_talents: int = Field(default=0, description="All talent profiles regardless of status")
    pending_talents: int = 0
    approved_talents: int = 0


class PublicStatsOut(BaseModel):
    """The homepage stats strip — approved-only, safe for an anonymous visitor."""

    total_businesses: int
    total_towns: int
    total_talents: int = 0

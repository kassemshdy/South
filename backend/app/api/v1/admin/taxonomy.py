"""Administrator CRUD for categories and locations."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.serializers import category_out, location_out
from app.core.dependencies import AdminUser, DbSession
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.i18n import translate
from app.models.taxonomy import Category, Location
from app.repositories.taxonomy import CategoryRepository, LocationRepository
from app.schemas.common import MessageResponse
from app.schemas.taxonomy import (
    CategoryIn,
    CategoryOut,
    CategoryUpdateIn,
    LocationIn,
    LocationOut,
    LocationUpdateIn,
)
from app.services.slug import slugify_name, unique_slug

router = APIRouter(prefix="/admin", tags=["admin-taxonomy"])


# --- Categories ------------------------------------------------------------


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    db: DbSession,
    admin: AdminUser,
    include_inactive: Annotated[bool, Query()] = True,
) -> list[CategoryOut]:
    categories = CategoryRepository(db).list_all(active_only=not include_inactive)
    return [out for c in categories if (out := category_out(c)) is not None]


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryIn, db: DbSession, admin: AdminUser) -> CategoryOut:
    repo = CategoryRepository(db)
    slug = (
        slugify_name(payload.slug)
        if payload.slug
        else unique_slug(payload.name_ar, repo.slug_exists)
    )
    if repo.slug_exists(slug):
        raise ConflictError("taxonomy.category.duplicate_slug", code="duplicate_slug")

    category = repo.add(
        Category(
            name_ar=payload.name_ar,
            slug=slug,
            icon=payload.icon,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
    )
    db.commit()
    out = category_out(category)
    assert out is not None
    return out


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: uuid.UUID, payload: CategoryUpdateIn, db: DbSession, admin: AdminUser
) -> CategoryOut:
    repo = CategoryRepository(db)
    category = repo.get(category_id)
    if category is None:
        raise NotFoundError("taxonomy.category.not_found")

    data = payload.model_dump(exclude_unset=True)
    if data.get("slug"):
        slug = slugify_name(data["slug"])
        if repo.slug_exists(slug, exclude_id=category_id):
            raise ConflictError("taxonomy.category.duplicate_slug", code="duplicate_slug")
        data["slug"] = slug

    for field, value in data.items():
        setattr(category, field, value)
    db.commit()
    out = category_out(category)
    assert out is not None
    return out


@router.delete("/categories/{category_id}", response_model=MessageResponse)
def delete_category(category_id: uuid.UUID, db: DbSession, admin: AdminUser) -> MessageResponse:
    repo = CategoryRepository(db)
    category = repo.get(category_id)
    if category is None:
        raise NotFoundError("taxonomy.category.not_found")
    if category.businesses:
        # Deactivating keeps existing listings intact; deleting would orphan them.
        raise ConflictError(
            "taxonomy.category.in_use",
            code="category_in_use",
        )
    repo.delete(category)
    db.commit()
    return MessageResponse(message=translate("taxonomy.category.deleted"))


# --- Locations -------------------------------------------------------------


@router.get("/locations", response_model=list[LocationOut])
def list_locations(
    db: DbSession, admin: AdminUser, include_inactive: Annotated[bool, Query()] = True
) -> list[LocationOut]:
    locations = LocationRepository(db).list_all(active_only=not include_inactive)
    return [out for loc in locations if (out := location_out(loc)) is not None]


@router.post("/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(payload: LocationIn, db: DbSession, admin: AdminUser) -> LocationOut:
    repo = LocationRepository(db)
    if payload.parent_id is not None and repo.get(payload.parent_id) is None:
        raise ValidationError("taxonomy.location.unknown_parent", code="unknown_parent")

    slug = (
        slugify_name(payload.slug)
        if payload.slug
        else unique_slug(payload.name_ar, repo.slug_exists)
    )
    if repo.slug_exists(slug):
        raise ConflictError("taxonomy.location.duplicate_slug", code="duplicate_slug")

    location = repo.add(
        Location(
            name_ar=payload.name_ar,
            slug=slug,
            type=payload.type,
            parent_id=payload.parent_id,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
    )
    db.commit()
    out = location_out(location)
    assert out is not None
    return out


@router.put("/locations/{location_id}", response_model=LocationOut)
def update_location(
    location_id: uuid.UUID, payload: LocationUpdateIn, db: DbSession, admin: AdminUser
) -> LocationOut:
    repo = LocationRepository(db)
    location = repo.get(location_id)
    if location is None:
        raise NotFoundError("taxonomy.location.not_found")

    data = payload.model_dump(exclude_unset=True)
    if data.get("parent_id") == location_id:
        raise ValidationError("taxonomy.location.self_parent", code="invalid_parent")
    if data.get("parent_id") is not None and repo.get(data["parent_id"]) is None:
        raise ValidationError("taxonomy.location.unknown_parent", code="unknown_parent")
    if data.get("slug"):
        slug = slugify_name(data["slug"])
        if repo.slug_exists(slug, exclude_id=location_id):
            raise ConflictError("taxonomy.location.duplicate_slug", code="duplicate_slug")
        data["slug"] = slug

    for field, value in data.items():
        setattr(location, field, value)
    db.commit()
    out = location_out(location)
    assert out is not None
    return out


@router.delete("/locations/{location_id}", response_model=MessageResponse)
def delete_location(location_id: uuid.UUID, db: DbSession, admin: AdminUser) -> MessageResponse:
    repo = LocationRepository(db)
    location = repo.get(location_id)
    if location is None:
        raise NotFoundError("taxonomy.location.not_found")
    if location.businesses:
        raise ConflictError(
            "taxonomy.location.in_use",
            code="location_in_use",
        )
    if repo.has_children(location_id):
        raise ConflictError("taxonomy.location.has_children", code="location_has_children")

    repo.delete(location)
    db.commit()
    return MessageResponse(message=translate("taxonomy.location.deleted"))

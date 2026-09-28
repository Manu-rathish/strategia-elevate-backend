from typing import Literal

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.schemas import RoleProfileListRead
from app.store import store

router = APIRouter(prefix="/api/role_profiles", tags=["role profiles"])


@router.get("", response_model=RoleProfileListRead)
def list_role_profiles(
    q: str | None = None,
    family: str | None = None,
    status: Literal["active", "all"] = "active",
    user: CurrentUser = Depends(current_user),
) -> RoleProfileListRead:
    if not (user.is_hr or user.is_manager):
        raise ApiError(403, "FORBIDDEN", "Role profiles require HR or manager access.")
    items = list(store.role_profiles)
    if status == "active":
        items = [profile for profile in items if profile["status"] == "active"]
    if q:
        needle = q.strip().casefold()
        items = [profile for profile in items if needle in profile["title"].casefold()]
    if family:
        items = [profile for profile in items if profile["family"] == family]
    items.sort(key=lambda profile: profile["title"].casefold())
    return RoleProfileListRead(items=items, capabilities=store.capabilities)

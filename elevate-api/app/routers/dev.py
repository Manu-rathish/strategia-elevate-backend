from fastapi import APIRouter

from app.errors import ApiError
from app.schemas import DevPersonaListRead
from app.settings import get_settings
from app.store import store

router = APIRouter(prefix="/api/dev", tags=["development"])


@router.get("/personas", response_model=DevPersonaListRead)
def list_personas() -> DevPersonaListRead:
    if not get_settings().dev_endpoints:
        raise ApiError(404, "NOT_FOUND", "Endpoint not found.")
    organisation_names = {row["id"]: row["name"] for row in store.organisations}
    items = [
        {
            "username": identity["dev_login_key"],
            "display_name": identity["display_name"],
            "organization": organisation_names[identity["organization_id"]],
            "elevate_roles": sorted(store.elevate_roles_by_user_id.get(identity["id"], set())),
            "state": identity["state"],
        }
        for identity in store.auth_users
        if identity.get("dev_login_key")
    ]
    items.sort(key=lambda item: item["display_name"].casefold())
    return DevPersonaListRead(items=items)

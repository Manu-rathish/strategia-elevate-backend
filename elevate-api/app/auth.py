from dataclasses import dataclass

from fastapi import Header, Response

from app.errors import ApiError
from app.settings import get_settings
from app.store import store


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    organization_id: str
    display_name: str
    role: str
    elevate_roles: frozenset[str]
    managed_unit_ids: frozenset[str]
    employee_id: str | None

    @property
    def is_hr(self) -> bool:
        return "hr_admin" in self.elevate_roles

    @property
    def is_manager(self) -> bool:
        return "manager" in self.elevate_roles


def _descendant_ids(unit_id: str) -> set[str]:
    result = {unit_id}
    for child in store.children_by_parent_id.get(unit_id, []):
        result.update(_descendant_ids(child["id"]))
    return result


def current_user(response: Response, x_dev_user: str | None = Header(default=None)) -> CurrentUser:
    settings = get_settings()
    key = (x_dev_user or settings.default_dev_user).strip()
    identity = store.auth_user_by_dev_key.get(key)
    if identity is None:
        raise ApiError(401, "UNKNOWN_DEV_USER", f"No seeded user named {key!r}.")
    if identity.get("state") != "active":
        raise ApiError(401, "IDENTITY_DISABLED", f"Identity {key!r} is {identity['state']}.")

    response.headers["X-Dev-User-Resolved"] = key
    response.headers["X-Dev-User-Source"] = "header" if x_dev_user else "default"

    managed_ids: set[str] = set()
    for unit in store.units_managed_by_user_id.get(identity["id"], []):
        managed_ids.update(_descendant_ids(unit["id"]))
    employee = store.employee_by_auth_user_id.get(identity["id"])
    return CurrentUser(
        user_id=identity["id"],
        organization_id=identity["organization_id"],
        display_name=identity["display_name"],
        role=identity["role"],
        elevate_roles=frozenset(store.elevate_roles_by_user_id.get(identity["id"], set())),
        managed_unit_ids=frozenset(managed_ids),
        employee_id=employee["id"] if employee else None,
    )

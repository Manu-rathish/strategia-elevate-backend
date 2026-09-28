from datetime import UTC, datetime
from uuid import uuid4

from app.auth import CurrentUser
from app.errors import ApiError
from app.schemas import OrgUnitCreate, OrgUnitRead, OrgUnitUpdate, OrgUnitWriteRead
from app.scoping import visible_employees
from app.store import Record, store


def visible_units(user: CurrentUser) -> list[Record]:
    organisation_units = store.units_by_org.get(user.organization_id, [])
    if user.is_hr:
        return organisation_units
    unit_ids: set[str] = set()
    if user.is_manager:
        unit_ids.update(user.managed_unit_ids)
    if "employee" in user.elevate_roles and user.employee_id:
        unit_ids.add(store.employees_by_id[user.employee_id]["org_unit_id"])
    if not user.elevate_roles:
        raise ApiError(403, "FORBIDDEN", "No Elevate role permits this request.")
    for unit_id in list(unit_ids):
        parent_id = store.units_by_id[unit_id].get("parent_id")
        while parent_id:
            unit_ids.add(parent_id)
            parent_id = store.units_by_id[parent_id].get("parent_id")
    return [unit for unit in organisation_units if unit["id"] in unit_ids]


def shape_unit(
    unit: Record,
    user: CurrentUser,
    include_counts: bool = True,
    allowed_unit_ids: set[str] | None = None,
) -> OrgUnitRead:
    identity = store.auth_user_by_id.get(unit.get("manager_user_id"))
    manager = None
    if identity and identity.get("state") == "active":
        manager = {"user_id": identity["id"], "display_name": identity["display_name"]}
    values = {
        "id": unit["id"],
        "name": unit["name"],
        "kind": unit["kind"],
        "parent_id": unit.get("parent_id"),
        "manager": manager,
        "is_active": unit["is_active"],
    }
    if include_counts:
        descendant_ids = {unit["id"]}
        pending = [unit["id"]]
        while pending:
            children = store.children_by_parent_id.get(pending.pop(), [])
            child_ids = [
                child["id"]
                for child in children
                if allowed_unit_ids is None or child["id"] in allowed_unit_ids
            ]
            descendant_ids.update(child_ids)
            pending.extend(child_ids)
        employees = [
            row
            for row in visible_employees(user)
            if row["org_unit_id"] in descendant_ids
        ]
        counts = {
            state: sum(row["status"] == state for row in employees)
            for state in ("active", "on_leave", "exited")
        }
        counts["total_visible"] = counts["active"] + counts["on_leave"]
        values["counts"] = counts
    return OrgUnitRead(**values)


def _require_hr(user: CurrentUser) -> None:
    if not user.is_hr:
        raise ApiError(403, "FORBIDDEN", "HR administrator access is required.")


def _validate_unique_name(name: str, user: CurrentUser, excluding_id: str | None = None) -> None:
    if any(
        unit["id"] != excluding_id and unit["name"].casefold() == name.casefold()
        for unit in store.units_by_org.get(user.organization_id, [])
    ):
        raise ApiError(409, "ORG_UNIT_NAME_TAKEN", f"Organisation unit {name!r} already exists.")


def _validate_parent(parent_id: str | None, user: CurrentUser) -> Record:
    if parent_id is None:
        raise ApiError(422, "PARENT_MUST_BE_DEPARTMENT", "A team's parent must be a department.")
    parent = store.units_by_id.get(parent_id)
    if parent is None or parent["organization_id"] != user.organization_id:
        raise ApiError(404, "ORG_UNIT_NOT_FOUND", "Parent organisation unit not found.")
    if parent["kind"] != "department":
        raise ApiError(422, "PARENT_MUST_BE_DEPARTMENT", "A team's parent must be a department.")
    return parent


def _validate_manager(manager_user_id: str | None, user: CurrentUser) -> None:
    if manager_user_id is None:
        return
    identity = store.auth_user_by_id.get(manager_user_id)
    employee = store.employee_by_auth_user_id.get(manager_user_id)
    if (
        identity is None
        or identity["organization_id"] != user.organization_id
        or identity["state"] != "active"
        or employee is None
        or employee["organization_id"] != user.organization_id
        or employee["status"] != "active"
    ):
        raise ApiError(422, "MANAGER_NOT_ELIGIBLE", "Manager must be a linked active employee.")


def create_unit(payload: OrgUnitCreate, user: CurrentUser) -> OrgUnitWriteRead:
    _require_hr(user)
    name = payload.name.strip()
    _validate_unique_name(name, user)
    if payload.kind == "department" and payload.parent_id is not None:
        raise ApiError(422, "DEPARTMENT_MUST_BE_ROOT", "Departments must be root units.")
    if payload.kind == "team":
        _validate_parent(payload.parent_id, user)
    _validate_manager(payload.manager_user_id, user)
    unit: Record = {
        "id": str(uuid4()),
        "ref": f"unit_{uuid4().hex[:8]}",
        "organization_id": user.organization_id,
        "name": name,
        "kind": payload.kind,
        "parent_id": payload.parent_id,
        "manager_user_id": payload.manager_user_id,
        "is_active": True,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    store.org_units.append(unit)
    store.rebuild_indexes()
    return OrgUnitWriteRead(unit=shape_unit(unit, user), employees_affected=0)


def update_unit(unit_id: str, payload: OrgUnitUpdate, user: CurrentUser) -> OrgUnitWriteRead:
    unit = store.units_by_id.get(unit_id)
    if unit is None or unit["organization_id"] != user.organization_id:
        raise ApiError(404, "ORG_UNIT_NOT_FOUND", "Organisation unit not found.")
    _require_hr(user)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        _validate_unique_name(changes["name"], user, unit_id)
    if "parent_id" in changes:
        parent_id = changes["parent_id"]
        if unit["kind"] == "department" and parent_id is not None:
            descendants = descendant_unit_ids(unit_id)
            if parent_id in descendants:
                raise ApiError(422, "ORG_UNIT_CYCLE", "A unit cannot move under its descendant.")
            raise ApiError(422, "PARENT_MUST_BE_DEPARTMENT", "Departments cannot be reparented.")
        if unit["kind"] == "team":
            _validate_parent(parent_id, user)
    if "manager_user_id" in changes:
        _validate_manager(changes["manager_user_id"], user)

    occupied_unit_ids = descendant_unit_ids(unit_id) | {unit_id}
    employee_count = sum(
        len(store.employees_by_unit.get(occupied_unit_id, []))
        for occupied_unit_id in occupied_unit_ids
    )
    if changes.get("is_active") is False and employee_count:
        raise ApiError(
            409,
            "ORG_UNIT_NOT_EMPTY",
            "An organisation unit with employees cannot be deactivated.",
            {"count": employee_count},
        )
    employees_affected = (
        len(store.employees_by_unit.get(unit_id, [])) if "parent_id" in changes else 0
    )
    unit.update(changes)
    store.rebuild_indexes()
    return OrgUnitWriteRead(
        unit=shape_unit(unit, user),
        employees_affected=employees_affected,
    )


def descendant_unit_ids(unit_id: str) -> set[str]:
    result: set[str] = set()
    pending = [unit_id]
    while pending:
        current = pending.pop()
        for child in store.children_by_parent_id.get(current, []):
            if child["id"] not in result:
                result.add(child["id"])
                pending.append(child["id"])
    return result

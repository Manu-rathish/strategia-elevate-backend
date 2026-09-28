from fastapi import APIRouter, Depends

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.schemas import OrgUnitListRead
from app.scoping import visible_employees
from app.store import Record, store

router = APIRouter(prefix="/api/org_units", tags=["organisation units"])


def _visible_units(user: CurrentUser) -> list[Record]:
    organisation_units = store.units_by_org.get(user.organization_id, [])
    if user.is_hr:
        return organisation_units
    unit_ids: set[str] = set()
    if user.is_manager:
        unit_ids.update(user.managed_unit_ids)
    if "employee" in user.elevate_roles and user.employee_id:
        employee = store.employees_by_id[user.employee_id]
        unit_ids.add(employee["org_unit_id"])
    if not user.elevate_roles:
        raise ApiError(403, "FORBIDDEN", "No Elevate role permits this request.")
    for unit_id in list(unit_ids):
        parent_id = store.units_by_id[unit_id].get("parent_id")
        while parent_id:
            unit_ids.add(parent_id)
            parent_id = store.units_by_id[parent_id].get("parent_id")
    return [unit for unit in organisation_units if unit["id"] in unit_ids]


@router.get("", response_model=OrgUnitListRead, response_model_exclude_unset=True)
def list_org_units(
    include_counts: bool = True, user: CurrentUser = Depends(current_user)
) -> OrgUnitListRead:
    visible_units = _visible_units(user)
    visible_employee_rows = visible_employees(user)
    allowed_unit_ids = {unit["id"] for unit in visible_units}
    items = []
    for unit in visible_units:
        manager = None
        identity = store.auth_user_by_id.get(unit.get("manager_user_id"))
        if identity and identity.get("state") == "active":
            manager = {"user_id": identity["id"], "display_name": identity["display_name"]}
        item = {
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
                child_ids = [
                    row["id"]
                    for row in store.children_by_parent_id.get(pending.pop(), [])
                    if row["id"] in allowed_unit_ids
                ]
                descendant_ids.update(child_ids)
                pending.extend(child_ids)
            employees = [
                row for row in visible_employee_rows if row["org_unit_id"] in descendant_ids
            ]
            counts = {
                state: sum(row["status"] == state for row in employees)
                for state in ("active", "on_leave", "exited")
            }
            counts["total_visible"] = counts["active"] + counts["on_leave"]
            item["counts"] = counts
        items.append(item)
    return OrgUnitListRead(items=items)

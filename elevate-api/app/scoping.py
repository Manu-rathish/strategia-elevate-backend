from app.auth import CurrentUser
from app.errors import ApiError
from app.schemas import EmployeeRead
from app.store import Record, store


def visible_employees(user: CurrentUser) -> list[Record]:
    if not user.elevate_roles:
        raise ApiError(403, "FORBIDDEN", "No Elevate role permits this request.")

    visible_ids: set[str] = set()
    organisation_employees = store.employees_by_org.get(user.organization_id, [])
    if user.is_hr:
        visible_ids.update(row["id"] for row in organisation_employees)
    if user.is_manager:
        visible_ids.update(
            row["id"]
            for unit_id in user.managed_unit_ids
            for row in store.employees_by_unit.get(unit_id, [])
            if row["organization_id"] == user.organization_id
        )
    if "employee" in user.elevate_roles and user.employee_id:
        visible_ids.add(user.employee_id)
    return [row for row in organisation_employees if row["id"] in visible_ids]


def shape_employee(employee: Record, user: CurrentUser) -> EmployeeRead:
    unit = store.units_by_id[employee["org_unit_id"]]
    department = None
    if unit.get("parent_id"):
        parent = store.units_by_id[unit["parent_id"]]
        department = {"id": parent["id"], "name": parent["name"]}

    anchor = store.current_anchor_by_employee_id.get(employee["id"])
    role_anchor = None
    if anchor:
        profile = store.role_profile_by_id.get(anchor["role_profile_id"])
        role_anchor = {
            "role_profile_id": anchor["role_profile_id"],
            "title": profile["title"]
            if profile
            else anchor.get("role_profile_ref", "Unknown role"),
            "effective_from": anchor["effective_from"],
        }

    manager = None
    manager_identity = store.auth_user_by_id.get(unit.get("manager_user_id"))
    if manager_identity and manager_identity.get("state") == "active":
        manager = {
            "user_id": manager_identity["id"],
            "display_name": manager_identity["display_name"],
        }

    values = {
        "id": employee["id"],
        "employee_number": employee["employee_number"],
        "first_name": employee["first_name"],
        "last_name": employee["last_name"],
        "full_name": f"{employee['first_name']} {employee['last_name']}",
        "work_email": employee["work_email"],
        "status": employee["status"],
        "started_on": employee["started_on"],
        "exited_on": employee.get("exited_on"),
        "org_unit": {
            "id": unit["id"],
            "name": unit["name"],
            "kind": unit["kind"],
            "department": department,
        },
        "role_anchor": role_anchor,
        "manager": manager,
        "is_manager": bool(store.units_managed_by_user_id.get(employee.get("auth_user_id", ""))),
        "created_at": employee["created_at"],
    }
    if user.is_hr:
        identity = store.auth_user_by_id.get(employee.get("auth_user_id"))
        values["identity"] = (
            {"state": identity["state"], "email": identity["email"]}
            if identity
            else {"state": "none"}
        )
        values["candidate_assessment_id"] = employee.get("candidate_assessment_id")
    return EmployeeRead(**values)


def get_visible_employee(employee_id: str, user: CurrentUser) -> Record:
    visible = {row["id"]: row for row in visible_employees(user)}
    employee = visible.get(employee_id)
    if employee is None:
        raise ApiError(404, "NOT_FOUND", "Employee not found.")
    return employee

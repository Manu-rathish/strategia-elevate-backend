from datetime import UTC, datetime
from math import ceil
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, status

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.schemas import (
    EmployeeCreate,
    EmployeeListRead,
    EmployeeRead,
    EmployeeUpdate,
    LifecycleResultRead,
    LifecycleUpdate,
)
from app.scoping import get_visible_employee, shape_employee, visible_employees
from app.store import Record, store

router = APIRouter(prefix="/api/employees", tags=["employees"])
VALID_STATUSES = {"active", "on_leave", "exited"}


def _require_hr(user: CurrentUser) -> None:
    if not user.is_hr:
        raise ApiError(403, "FORBIDDEN", "HR administrator access is required.")


def _parse_statuses(raw: str) -> set[str]:
    values = {value.strip() for value in raw.split(",") if value.strip()}
    if not values or not values <= VALID_STATUSES:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "status must contain active, on_leave, or exited.",
            {"field": "status"},
        )
    return values


def _unit_filter_ids(unit_id: str, user: CurrentUser) -> set[str]:
    unit = store.units_by_id.get(unit_id)
    if unit is None or unit["organization_id"] != user.organization_id:
        raise ApiError(404, "ORG_UNIT_NOT_FOUND", "Organisation unit not found.")
    result = {unit_id}
    pending = [unit_id]
    while pending:
        parent_id = pending.pop()
        child_ids = [row["id"] for row in store.children_by_parent_id.get(parent_id, [])]
        result.update(child_ids)
        pending.extend(child_ids)
    return result


def _validate_team(unit_id: str, user: CurrentUser) -> None:
    unit = store.units_by_id.get(unit_id)
    if unit is None or unit["organization_id"] != user.organization_id:
        raise ApiError(404, "ORG_UNIT_NOT_FOUND", "Organisation unit not found.")
    if unit["kind"] != "team":
        raise ApiError(422, "TEAM_EXPECTED", "org_unit_id must identify a team.")


def _ensure_unique(
    field: Literal["employee_number", "work_email"],
    value: str,
    user: CurrentUser,
    excluding_id: str | None = None,
) -> None:
    collision = next(
        (
            row
            for row in store.employees_by_org.get(user.organization_id, [])
            if row["id"] != excluding_id and row[field].casefold() == value.casefold()
        ),
        None,
    )
    if collision:
        code = "EMPLOYEE_NUMBER_TAKEN" if field == "employee_number" else "EMAIL_TAKEN"
        label = "Employee number" if field == "employee_number" else "Work email"
        raise ApiError(
            409,
            code,
            f"{label} {value} is already in use.",
            {"field": field},
        )


@router.get("", response_model=EmployeeListRead, response_model_exclude_unset=True)
def list_employees(
    q: str | None = None,
    status_filter: str = Query("active,on_leave", alias="status"),
    org_unit_id: str | None = None,
    sort: Literal["name", "employee_number", "started_on"] = "name",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user: CurrentUser = Depends(current_user),
) -> EmployeeListRead:
    visible = visible_employees(user)
    summary = {
        state: sum(row["status"] == state for row in visible)
        for state in ("active", "on_leave", "exited")
    }
    summary["total"] = len(visible)

    selected_statuses = _parse_statuses(status_filter)
    filtered = [row for row in visible if row["status"] in selected_statuses]
    if q and len(q.strip()) >= 2:
        needle = q.strip().casefold()
        filtered = [
            row
            for row in filtered
            if any(
                needle in str(row[field]).casefold()
                for field in ("first_name", "last_name", "work_email", "employee_number")
            )
        ]
    if org_unit_id:
        unit_ids = _unit_filter_ids(org_unit_id, user)
        filtered = [row for row in filtered if row["org_unit_id"] in unit_ids]

    if sort == "name":
        key = lambda row: (row["last_name"].casefold(), row["first_name"].casefold())
    elif sort == "employee_number":
        key = lambda row: row["employee_number"].casefold()
    else:
        key = lambda row: row["started_on"]
    filtered.sort(key=key, reverse=order == "desc")

    total = len(filtered)
    start = (page - 1) * page_size
    items = [shape_employee(row, user) for row in filtered[start : start + page_size]]
    return EmployeeListRead(
        items=items,
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": ceil(total / page_size) if total else 0,
        },
        summary=summary,
    )


@router.get("/{employee_id}", response_model=EmployeeRead, response_model_exclude_unset=True)
def get_employee(employee_id: str, user: CurrentUser = Depends(current_user)) -> EmployeeRead:
    return shape_employee(get_visible_employee(employee_id, user), user)


@router.post(
    "",
    response_model=EmployeeRead,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    payload: EmployeeCreate, user: CurrentUser = Depends(current_user)
) -> EmployeeRead:
    _require_hr(user)
    _validate_team(payload.org_unit_id, user)
    _ensure_unique("employee_number", payload.employee_number, user)
    _ensure_unique("work_email", payload.work_email, user)
    if payload.status == "exited" and payload.exited_on is None:
        raise ApiError(400, "EXIT_DATE_REQUIRED", "An exit date is required for exited employees.")
    if payload.status != "exited" and payload.exited_on is not None:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "exited_on may only be set when status is exited.",
            {"field": "exited_on"},
        )
    employee: Record = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        **payload.model_dump(mode="json"),
        "auth_user_id": None,
        "is_manager": False,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "created_by": user.user_id,
    }
    store.employees.append(employee)
    store.rebuild_indexes()
    return shape_employee(employee, user)


@router.patch("/{employee_id}", response_model=EmployeeRead, response_model_exclude_unset=True)
def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    user: CurrentUser = Depends(current_user),
) -> EmployeeRead:
    employee = store.employees_by_id.get(employee_id)
    if employee is None or employee["organization_id"] != user.organization_id:
        raise ApiError(404, "NOT_FOUND", "Employee not found.")
    _require_hr(user)
    changes = payload.model_dump(exclude_unset=True, mode="json")
    if "org_unit_id" in changes:
        _validate_team(changes["org_unit_id"], user)
    if "work_email" in changes:
        _ensure_unique("work_email", changes["work_email"], user, employee_id)
    employee.update(changes)
    store.rebuild_indexes()
    return shape_employee(employee, user)


@router.post(
    "/{employee_id}/lifecycle",
    response_model=LifecycleResultRead,
    response_model_exclude_unset=True,
)
def update_lifecycle(
    employee_id: str,
    payload: LifecycleUpdate,
    user: CurrentUser = Depends(current_user),
) -> LifecycleResultRead:
    employee = store.employees_by_id.get(employee_id)
    if employee is None or employee["organization_id"] != user.organization_id:
        raise ApiError(404, "NOT_FOUND", "Employee not found.")
    _require_hr(user)
    old_status = employee["status"]
    new_status = payload.status
    if new_status == "exited" and payload.effective_on is None:
        raise ApiError(400, "EXIT_DATE_REQUIRED", "An exit date is required for exited employees.")
    if payload.effective_on is None:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "effective_on is required.",
            {"field": "effective_on"},
        )
    allowed = {
        ("active", "on_leave"),
        ("on_leave", "active"),
        ("active", "exited"),
        ("on_leave", "exited"),
    }
    if old_status == "exited" or (old_status, new_status) not in allowed:
        raise ApiError(
            409,
            "INVALID_LIFECYCLE_TRANSITION",
            f"Cannot transition an employee from {old_status} to {new_status}.",
        )
    employee["status"] = new_status
    employee["exited_on"] = payload.effective_on.isoformat() if new_status == "exited" else None
    warnings = []
    if new_status == "exited" and employee.get("auth_user_id"):
        managed = store.units_managed_by_user_id.get(employee["auth_user_id"], [])
        if managed:
            warnings.append(
                {
                    "code": "TEAM_LEFT_WITHOUT_MANAGER",
                    "org_unit_ids": [unit["id"] for unit in managed],
                }
            )
    store.rebuild_indexes()
    return LifecycleResultRead(employee=shape_employee(employee, user), warnings=warnings)

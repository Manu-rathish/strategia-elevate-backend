from fastapi import APIRouter, Depends

from app.audit import record_access
from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.role_anchor_service import assign_role_anchor, shape_role_anchors
from app.schemas import RoleAnchorListRead, RoleAnchorWrite
from app.scoping import get_visible_employee
from app.store import store

router = APIRouter(prefix="/api/employees", tags=["role anchors"])


@router.get("/{employee_id}/role_anchors", response_model=RoleAnchorListRead)
def list_role_anchors(
    employee_id: str,
    user: CurrentUser = Depends(current_user),
) -> RoleAnchorListRead:
    employee = get_visible_employee(employee_id, user)
    result = shape_role_anchors(employee["id"])
    record_access(user, "role_anchor_history", employee["id"])
    return result


@router.put("/{employee_id}/role_anchor", response_model=RoleAnchorListRead)
def update_role_anchor(
    employee_id: str,
    payload: RoleAnchorWrite,
    user: CurrentUser = Depends(current_user),
) -> RoleAnchorListRead:
    employee = store.employees_by_id.get(employee_id)
    if employee is None or employee["organization_id"] != user.organization_id:
        raise ApiError(404, "NOT_FOUND", "Employee not found.")
    if not user.is_hr:
        raise ApiError(403, "FORBIDDEN", "HR administrator access is required.")
    return assign_role_anchor(employee, payload, user)

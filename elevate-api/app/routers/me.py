from fastapi import APIRouter, Depends

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.schemas import MeRead
from app.scoping import shape_employee
from app.store import store

router = APIRouter(prefix="/api", tags=["current user"])


@router.get("/me", response_model=MeRead, response_model_exclude_unset=True)
def get_me(user: CurrentUser = Depends(current_user)) -> MeRead:
    if user.employee_id is None:
        raise ApiError(404, "NO_EMPLOYEE_RECORD", "This identity has no employee record.")
    if not user.elevate_roles:
        raise ApiError(403, "FORBIDDEN", "No Elevate role permits this request.")
    employee = store.employees_by_id[user.employee_id]
    return MeRead(
        user={
            "user_id": user.user_id,
            "display_name": user.display_name,
            "organization_id": user.organization_id,
            "role": user.role,
            "elevate_roles": sorted(user.elevate_roles),
            "managed_unit_ids": sorted(user.managed_unit_ids),
            "employee_id": user.employee_id,
        },
        employee=shape_employee(employee, user),
    )

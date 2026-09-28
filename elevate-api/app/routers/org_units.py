from fastapi import APIRouter, Depends, status

from app.auth import CurrentUser, current_user
from app.org_unit_service import create_unit, shape_unit, update_unit, visible_units
from app.schemas import (
    OrgUnitCreate,
    OrgUnitListRead,
    OrgUnitUpdate,
    OrgUnitWriteRead,
)

router = APIRouter(prefix="/api/org_units", tags=["organisation units"])


@router.get("", response_model=OrgUnitListRead, response_model_exclude_unset=True)
def list_org_units(
    include_counts: bool = True, user: CurrentUser = Depends(current_user)
) -> OrgUnitListRead:
    units = visible_units(user)
    allowed_unit_ids = {unit["id"] for unit in units}
    items = [shape_unit(unit, user, include_counts, allowed_unit_ids) for unit in units]
    return OrgUnitListRead(items=items)


@router.post("", response_model=OrgUnitWriteRead, status_code=status.HTTP_201_CREATED)
def create_org_unit(
    payload: OrgUnitCreate,
    user: CurrentUser = Depends(current_user),
) -> OrgUnitWriteRead:
    return create_unit(payload, user)


@router.patch("/{unit_id}", response_model=OrgUnitWriteRead)
def patch_org_unit(
    unit_id: str,
    payload: OrgUnitUpdate,
    user: CurrentUser = Depends(current_user),
) -> OrgUnitWriteRead:
    return update_unit(unit_id, payload, user)

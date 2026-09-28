from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EmployeeStatus = Literal["active", "on_leave", "exited"]


class DepartmentRead(BaseModel):
    id: str
    name: str


class EmployeeOrgUnitRead(BaseModel):
    id: str
    name: str
    kind: Literal["department", "team"]
    department: DepartmentRead | None


class RoleAnchorRead(BaseModel):
    role_profile_id: str
    title: str
    effective_from: date


class ManagerRead(BaseModel):
    user_id: str
    display_name: str


class IdentityRead(BaseModel):
    state: str
    email: str


class EmployeeRead(BaseModel):
    id: str
    employee_number: str
    first_name: str
    last_name: str
    full_name: str
    work_email: str
    status: EmployeeStatus
    started_on: date
    exited_on: date | None
    org_unit: EmployeeOrgUnitRead
    role_anchor: RoleAnchorRead | None
    manager: ManagerRead | None
    is_manager: bool
    identity: IdentityRead | None = None
    created_at: str
    candidate_assessment_id: str | None = None


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_number: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    work_email: str = Field(min_length=3)
    status: EmployeeStatus = "active"
    started_on: date
    exited_on: date | None = None
    org_unit_id: str
    candidate_assessment_id: str | None = None


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    work_email: str | None = Field(default=None, min_length=3)
    org_unit_id: str | None = None
    started_on: date | None = None
    candidate_assessment_id: str | None = None

    @model_validator(mode="after")
    def reject_null_required_values(self) -> "EmployeeUpdate":
        nullable_only = {"candidate_assessment_id"}
        invalid = [
            field for field in self.model_fields_set - nullable_only if getattr(self, field) is None
        ]
        if invalid:
            raise ValueError(f"Fields may not be null: {', '.join(sorted(invalid))}")
        return self


class LifecycleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EmployeeStatus
    effective_on: date | None = None
    reason: str | None = None


class PaginationRead(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class EmployeeSummaryRead(BaseModel):
    active: int
    on_leave: int
    exited: int
    total: int


class EmployeeListRead(BaseModel):
    items: list[EmployeeRead]
    pagination: PaginationRead
    summary: EmployeeSummaryRead


class CurrentUserRead(BaseModel):
    user_id: str
    display_name: str
    organization_id: str
    role: str
    elevate_roles: list[str]
    managed_unit_ids: list[str]
    employee_id: str | None


class MeRead(BaseModel):
    user: CurrentUserRead
    employee: EmployeeRead


class WarningRead(BaseModel):
    code: str
    org_unit_ids: list[str]


class LifecycleResultRead(BaseModel):
    employee: EmployeeRead
    warnings: list[WarningRead]


class UnitManagerRead(BaseModel):
    user_id: str
    display_name: str


class UnitCountsRead(BaseModel):
    active: int
    on_leave: int
    exited: int
    total_visible: int


class OrgUnitRead(BaseModel):
    id: str
    name: str
    kind: Literal["department", "team"]
    parent_id: str | None
    manager: UnitManagerRead | None
    is_active: bool
    counts: UnitCountsRead | None = None


class OrgUnitListRead(BaseModel):
    items: list[OrgUnitRead]

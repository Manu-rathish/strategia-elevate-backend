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
    email: str | None = None


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


class DevPersonaRead(BaseModel):
    username: str
    display_name: str
    organization: str
    elevate_roles: list[str]
    state: Literal["active", "invited", "disabled"]


class DevPersonaListRead(BaseModel):
    items: list[DevPersonaRead]


class CapabilityRead(BaseModel):
    key: str
    label: str


class RoleProfileCompetencyRead(CapabilityRead):
    required_level: int


class RoleProfileRead(BaseModel):
    id: str
    ref: str
    title: str
    family: str
    status: Literal["active", "archived"]
    scale: dict[str, int | str]
    competencies: list[RoleProfileCompetencyRead]


class RoleProfileListRead(BaseModel):
    items: list[RoleProfileRead]
    capabilities: list[CapabilityRead]


class RoleAnchorProfileRead(BaseModel):
    id: str
    ref: str
    title: str
    family: str
    status: Literal["active", "archived"]


class RoleAnchorHistoryRead(BaseModel):
    id: str
    effective_from: date
    effective_to: date | None
    role_profile: RoleAnchorProfileRead
    assigned_by: ManagerRead
    reason: str
    created_at: str


class RoleAnchorListRead(BaseModel):
    items: list[RoleAnchorHistoryRead]


class RoleAnchorWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_profile_id: str
    effective_from: date
    reason: str | None = None


class OrgUnitCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    kind: Literal["department", "team"]
    parent_id: str | None
    manager_user_id: str | None = None


class OrgUnitUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    parent_id: str | None = None
    manager_user_id: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_values(self) -> "OrgUnitUpdate":
        invalid = [
            field
            for field in self.model_fields_set - {"parent_id", "manager_user_id"}
            if getattr(self, field) is None
        ]
        if invalid:
            raise ValueError(f"Fields may not be null: {', '.join(sorted(invalid))}")
        return self


class OrgUnitWriteRead(BaseModel):
    unit: OrgUnitRead
    employees_affected: int

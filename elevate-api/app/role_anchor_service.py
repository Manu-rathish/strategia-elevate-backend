from datetime import UTC, date, datetime
from uuid import uuid4

from app.auth import CurrentUser
from app.errors import ApiError
from app.schemas import RoleAnchorListRead, RoleAnchorWrite
from app.store import Record, store


def shape_role_anchors(employee_id: str) -> RoleAnchorListRead:
    items = []
    anchors = sorted(
        store.role_anchors_by_employee_id.get(employee_id, []),
        key=lambda row: row["effective_from"],
        reverse=True,
    )
    for anchor in anchors:
        profile = store.role_profile_by_id[anchor["role_profile_id"]]
        assigned_by = store.auth_user_by_id[anchor["assigned_by_user_id"]]
        items.append(
            {
                "id": anchor["id"],
                "effective_from": anchor["effective_from"],
                "effective_to": anchor.get("effective_to"),
                "role_profile": {
                    key: profile[key]
                    for key in ("id", "ref", "title", "family", "status")
                },
                "assigned_by": {
                    "user_id": assigned_by["id"],
                    "display_name": assigned_by["display_name"],
                },
                "reason": anchor["reason"],
                "created_at": anchor["created_at"],
            }
        )
    return RoleAnchorListRead(items=items)


def assign_role_anchor(
    employee: Record,
    payload: RoleAnchorWrite,
    user: CurrentUser,
) -> RoleAnchorListRead:
    reason = (payload.reason or "").strip()
    if not reason:
        raise ApiError(400, "ANCHOR_REASON_REQUIRED", "A reason is required.")

    profile = store.role_profile_by_id.get(payload.role_profile_id)
    if profile is None:
        raise ApiError(404, "ROLE_PROFILE_NOT_FOUND", "Role profile not found.")
    if profile["status"] != "active":
        raise ApiError(422, "ROLE_PROFILE_ARCHIVED", "Archived role profiles cannot be assigned.")

    current = store.current_anchor_by_employee_id.get(employee["id"])
    effective_from = payload.effective_from.isoformat()
    if current:
        current_from = date.fromisoformat(current["effective_from"])
        if payload.effective_from < current_from:
            raise ApiError(
                422,
                "ANCHOR_DATE_BEFORE_CURRENT",
                "The new anchor cannot start before the current anchor.",
            )
        if payload.effective_from == current_from:
            current.update(
                role_profile_id=profile["id"],
                role_profile_ref=profile["ref"],
                reason=reason,
            )
            store.rebuild_indexes()
            return shape_role_anchors(employee["id"])
        current["effective_to"] = effective_from

    anchor: Record = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        "employee_id": employee["id"],
        "employee_ref": employee.get("ref", employee["employee_number"]),
        "role_profile_id": profile["id"],
        "role_profile_ref": profile["ref"],
        "effective_from": effective_from,
        "effective_to": None,
        "assigned_by_user_id": user.user_id,
        "reason": reason,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    store.role_anchors.append(anchor)
    store.rebuild_indexes()
    return shape_role_anchors(employee["id"])

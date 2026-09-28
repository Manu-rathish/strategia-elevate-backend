from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from app.auth import CurrentUser

AccessView = Literal["employee_list", "employee_detail", "role_anchor_history", "my_record"]

access_log: list[dict[str, str | None]] = []


def record_access(
    user: CurrentUser,
    view: AccessView,
    subject_employee_id: str | None = None,
) -> None:
    access_log.append(
        {
            "id": str(uuid4()),
            "organization_id": user.organization_id,
            "actor_user_id": user.user_id,
            "actor_display_name": user.display_name,
            "subject_employee_id": subject_employee_id,
            "view": view,
            "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "correlation_id": uuid4().hex[:8],
        }
    )

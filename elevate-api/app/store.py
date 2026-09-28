import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.settings import get_settings

Record = dict[str, Any]


def _load(seed_dir: Path, name: str) -> Any:
    with (seed_dir / name).open(encoding="utf-8") as source:
        return json.load(source)


class Store:
    def __init__(self, seed_dir: Path) -> None:
        self.organisations: list[Record] = _load(seed_dir, "organisations.json")
        self.employees: list[Record] = _load(seed_dir, "employees.json")
        self.org_units: list[Record] = _load(seed_dir, "org_units.json")
        self.auth_users: list[Record] = _load(seed_dir, "auth_users.json")
        self.user_pillar_roles: list[Record] = _load(seed_dir, "user_pillar_roles.json")
        self.role_anchors: list[Record] = _load(seed_dir, "role_anchors.json")
        profiles = _load(seed_dir, "vjob-role-profiles.json")
        self.capabilities: list[Record] = profiles["capabilities"]
        self.role_profiles: list[Record] = profiles["role_profiles"]
        self.rebuild_indexes()

    def rebuild_indexes(self) -> None:
        self.employees_by_id = {row["id"]: row for row in self.employees}
        self.employees_by_org = self._group(self.employees, "organization_id")
        self.employees_by_unit = self._group(self.employees, "org_unit_id")
        self.employee_by_auth_user_id = {
            row["auth_user_id"]: row for row in self.employees if row.get("auth_user_id")
        }
        self.units_by_id = {row["id"]: row for row in self.org_units}
        self.units_by_org = self._group(self.org_units, "organization_id")
        self.children_by_parent_id = self._group(
            [row for row in self.org_units if row.get("parent_id")], "parent_id"
        )
        self.auth_user_by_dev_key = {
            row["dev_login_key"]: row for row in self.auth_users if row.get("dev_login_key")
        }
        self.auth_user_by_id = {row["id"]: row for row in self.auth_users}
        roles: dict[str, set[str]] = defaultdict(set)
        for row in self.user_pillar_roles:
            if row.get("pillar") == "elevate":
                roles[row["user_id"]].add(row["role"])
        self.elevate_roles_by_user_id = dict(roles)
        self.current_anchor_by_employee_id = {
            row["employee_id"]: row for row in self.role_anchors if row.get("effective_to") is None
        }
        self.role_anchors_by_employee_id = self._group(self.role_anchors, "employee_id")
        self.role_profile_by_id = {row["id"]: row for row in self.role_profiles}
        self.units_managed_by_user_id = self._group(
            [row for row in self.org_units if row.get("manager_user_id")], "manager_user_id"
        )

    @staticmethod
    def _group(rows: list[Record], key: str) -> dict[str, list[Record]]:
        grouped: dict[str, list[Record]] = defaultdict(list)
        for row in rows:
            grouped[row[key]].append(row)
        return dict(grouped)


store = Store(get_settings().resolved_seed_dir())

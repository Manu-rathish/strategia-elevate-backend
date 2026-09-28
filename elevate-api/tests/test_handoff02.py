from fastapi.testclient import TestClient

from app.audit import access_log
from app.store import store

JENNY = {"X-Dev-User": "jenny.marsh"}
AMELIA_ID = "649df16c-63db-56fd-8db6-dc2cdf4eb68c"
REGISTERED_NURSE_ID = "276041f4-64c1-5fff-a35f-101ecde12722"


def _unit_id(name: str) -> str:
    return next(unit["id"] for unit in store.org_units if unit["name"] == name)


def test_dev_personas_and_role_profiles(client: TestClient) -> None:
    personas = client.get("/api/dev/personas")
    assert personas.status_code == 200
    items = personas.json()["items"]
    assert len(items) == 57
    assert next(item for item in items if item["username"] == "robyn.ashcroft")["state"] == "disabled"
    assert next(item for item in items if item["username"] == "dana.oyelaran")["elevate_roles"] == []

    active = client.get("/api/role_profiles", headers=JENNY).json()
    all_profiles = client.get("/api/role_profiles?status=all", headers=JENNY).json()
    assert len(active["items"]) == 13
    assert len(all_profiles["items"]) == 14
    assert len(active["capabilities"]) == 6
    assert all(len(profile["competencies"]) == 6 for profile in all_profiles["items"])
    assert client.get(
        "/api/role_profiles", headers={"X-Dev-User": "james.whitfield"}
    ).status_code == 403


def test_role_anchor_history_scoping_and_half_open_dates(client: TestClient) -> None:
    path = f"/api/employees/{AMELIA_ID}/role_anchors"
    response = client.get(path, headers=JENNY)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert items[0]["effective_from"] == "2015-05-28"
    assert items[0]["effective_to"] is None
    assert items[1]["effective_to"] == "2015-05-28"
    assert items[1]["role_profile"]["status"] == "archived"
    assert client.get(path, headers={"X-Dev-User": "paul.henderson"}).status_code == 404
    assert client.get(path, headers={"X-Dev-User": "amelia.foster"}).status_code == 200
    assert client.get(path, headers={"X-Dev-User": "marion.teague"}).status_code == 404
    assert client.get(path, headers={"X-Dev-User": "dana.oyelaran"}).status_code == 403


def test_role_anchor_write_and_same_day_correction(client: TestClient) -> None:
    path = f"/api/employees/{AMELIA_ID}/role_anchor"
    payload = {
        "role_profile_id": REGISTERED_NURSE_ID,
        "effective_from": "2026-09-29",
        "reason": "Promotion",
    }
    first = client.put(path, headers=JENNY, json=payload)
    assert first.status_code == 200
    assert len(first.json()["items"]) == 3
    assert first.json()["items"][1]["effective_to"] == "2026-09-29"

    payload["reason"] = "Corrected reason"
    corrected = client.put(path, headers=JENNY, json=payload)
    assert len(corrected.json()["items"]) == 3
    assert corrected.json()["items"][0]["reason"] == "Corrected reason"

    archived_id = next(profile["id"] for profile in store.role_profiles if profile["ref"] == "en_2023")
    archived = client.put(path, headers=JENNY, json={**payload, "role_profile_id": archived_id})
    assert archived.status_code == 422
    assert archived.json()["error"]["code"] == "ROLE_PROFILE_ARCHIVED"
    before = client.put(path, headers=JENNY, json={**payload, "effective_from": "2010-01-01"})
    assert before.status_code == 422
    assert before.json()["error"]["code"] == "ANCHOR_DATE_BEFORE_CURRENT"
    missing_reason = client.put(path, headers=JENNY, json={key: value for key, value in payload.items() if key != "reason"})
    assert missing_reason.status_code == 400
    assert missing_reason.json()["error"]["code"] == "ANCHOR_REASON_REQUIRED"

    for anchors in store.role_anchors_by_employee_id.values():
        assert sum(anchor["effective_to"] is None for anchor in anchors) == 1


def test_org_unit_create_patch_and_validation(client: TestClient) -> None:
    nursing_id = _unit_id("Nursing")
    ward_4b_id = _unit_id("Ward 4B nursing")
    physiotherapy_id = _unit_id("Physiotherapy")
    ward_9_id = _unit_id("Ward 9 nursing (opening)")

    created = client.post(
        "/api/org_units",
        headers=JENNY,
        json={"name": "Ward 9 rehabilitation", "kind": "team", "parent_id": nursing_id},
    )
    assert created.status_code == 201
    assert created.json()["employees_affected"] == 0
    assert client.post(
        "/api/org_units",
        headers=JENNY,
        json={"name": "Nested team", "kind": "team", "parent_id": ward_4b_id},
    ).json()["error"]["code"] == "PARENT_MUST_BE_DEPARTMENT"
    assert client.post(
        "/api/org_units",
        headers=JENNY,
        json={"name": "Nested department", "kind": "department", "parent_id": nursing_id},
    ).json()["error"]["code"] == "DEPARTMENT_MUST_BE_ROOT"
    assert client.post(
        "/api/org_units",
        headers=JENNY,
        json={"name": "Nursing", "kind": "department", "parent_id": None},
    ).json()["error"]["code"] == "ORG_UNIT_NAME_TAKEN"

    nonempty = client.patch(
        f"/api/org_units/{physiotherapy_id}", headers=JENNY, json={"is_active": False}
    )
    assert nonempty.status_code == 409
    assert nonempty.json()["error"]["details"]["count"] == 9
    assert client.patch(
        f"/api/org_units/{ward_9_id}", headers=JENNY, json={"is_active": False}
    ).status_code == 200
    cycle = client.patch(
        f"/api/org_units/{nursing_id}", headers=JENNY, json={"parent_id": ward_4b_id}
    )
    assert cycle.status_code == 422
    assert cycle.json()["error"]["code"] == "ORG_UNIT_CYCLE"


def test_review_fixes_and_access_writes(client: TestClient) -> None:
    digital_id = _unit_id("Digital and data")
    summary = client.get(
        f"/api/employees?org_unit_id={digital_id}&status=active,on_leave,exited",
        headers=JENNY,
    ).json()["summary"]
    assert summary["total"] == 3

    no_identity = next(employee for employee in store.employees if not employee.get("auth_user_id"))
    shaped = client.get(f"/api/employees/{no_identity['id']}", headers=JENNY).json()
    assert shaped["identity"] == {"state": "none"}

    access_log.clear()
    client.get("/api/employees?page_size=25", headers=JENNY)
    client.get(f"/api/employees/{AMELIA_ID}", headers=JENNY)
    client.get("/api/me", headers=JENNY)
    client.get(f"/api/employees/{AMELIA_ID}/role_anchors", headers=JENNY)
    assert [row["view"] for row in access_log] == [
        "employee_list",
        "employee_detail",
        "my_record",
        "role_anchor_history",
    ]
    assert access_log[0]["subject_employee_id"] is None

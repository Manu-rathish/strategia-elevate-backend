from fastapi.testclient import TestClient


def test_health_and_hr_totals(client: TestClient) -> None:
    assert client.get("/health").json() == {
        "status": "ok",
        "employees": 118,
        "organisations": 2,
    }
    response = client.get("/api/employees?page_size=1", headers={"X-Dev-User": "jenny.marsh"})
    assert response.json()["summary"] == {
        "active": 97,
        "on_leave": 8,
        "exited": 7,
        "total": 112,
    }


def test_all_statuses(client: TestClient) -> None:
    response = client.get(
        "/api/employees?status=active,on_leave,exited&page_size=1",
        headers={"X-Dev-User": "jenny.marsh"},
    )
    assert response.json()["pagination"]["total"] == 112


def test_hr_fields_are_omitted_for_manager(client: TestClient) -> None:
    manager_list = client.get(
        "/api/employees?page_size=1", headers={"X-Dev-User": "paul.henderson"}
    ).json()
    manager_employee = manager_list["items"][0]
    assert "candidate_assessment_id" not in manager_employee
    assert "identity" not in manager_employee

    hr_employee = client.get(
        f"/api/employees/{manager_employee['id']}",
        headers={"X-Dev-User": "jenny.marsh"},
    ).json()
    assert "candidate_assessment_id" in hr_employee
    assert "identity" in hr_employee


def test_me_with_and_without_employee(client: TestClient) -> None:
    me_response = client.get("/api/me", headers={"X-Dev-User": "james.whitfield"})
    assert me_response.status_code == 200
    assert set(me_response.json()["user"]) == {
        "user_id",
        "display_name",
        "organization_id",
        "role",
        "elevate_roles",
        "managed_unit_ids",
        "employee_id",
    }
    assert me_response.json()["user"]["role"] == "employee"
    assert me_response.json()["user"]["employee_id"] == me_response.json()["employee"]["id"]
    response = client.get("/api/me", headers={"X-Dev-User": "dana.oyelaran"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NO_EMPLOYEE_RECORD"


def test_validation_errors_use_envelope(client: TestClient) -> None:
    response = client.get("/api/employees?page=0", headers={"X-Dev-User": "jenny.marsh"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_exiting_without_date_uses_domain_error(client: TestClient) -> None:
    response = client.post(
        "/api/employees/4a502299-0026-53c7-9670-1a015dff377a/lifecycle",
        headers={"X-Dev-User": "jenny.marsh"},
        json={"status": "exited", "reason": "Resignation"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EXIT_DATE_REQUIRED"

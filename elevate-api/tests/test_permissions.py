import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("dev_user", "status_code", "total", "error_code"),
    [
        ("jenny.marsh", 200, 105, None),
        ("helen.frost", 200, 105, None),
        ("paul.henderson", 200, 11, None),
        ("claire.doyle", 200, 12, None),
        ("arjun.mehta", 200, 3, None),
        ("james.whitfield", 200, 1, None),
        ("dana.oyelaran", 403, None, "FORBIDDEN"),
        ("marion.teague", 200, 6, None),
        ("robyn.ashcroft", 401, None, "IDENTITY_DISABLED"),
    ],
)
def test_visibility_matrix(
    client: TestClient,
    dev_user: str,
    status_code: int,
    total: int | None,
    error_code: str | None,
) -> None:
    response = client.get("/api/employees?page_size=1", headers={"X-Dev-User": dev_user})
    assert response.status_code == status_code
    if total is not None:
        assert response.json()["pagination"]["total"] == total
    else:
        assert response.json()["error"]["code"] == error_code


def test_missing_header_uses_default_dev_user(client: TestClient) -> None:
    response = client.get("/api/employees?page_size=1")
    assert response.status_code == 200
    assert response.json()["pagination"]["total"] == 105
    assert response.headers["X-Dev-User-Resolved"] == "jenny.marsh"
    assert response.headers["X-Dev-User-Source"] == "default"


def test_header_marks_resolved_user_source(client: TestClient) -> None:
    response = client.get("/api/employees?page_size=1", headers={"X-Dev-User": "paul.henderson"})
    assert response.status_code == 200
    assert response.json()["pagination"]["total"] == 11
    assert response.headers["X-Dev-User-Resolved"] == "paul.henderson"
    assert response.headers["X-Dev-User-Source"] == "header"


def test_unknown_dev_user(client: TestClient) -> None:
    response = client.get("/api/employees", headers={"X-Dev-User": "nobody.atall"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNKNOWN_DEV_USER"


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("get", "/api/employees/4a502299-0026-53c7-9670-1a015dff377a", None),
        (
            "patch",
            "/api/employees/4a502299-0026-53c7-9670-1a015dff377a",
            {"first_name": "Nope"},
        ),
        (
            "post",
            "/api/employees/4a502299-0026-53c7-9670-1a015dff377a/lifecycle",
            {"status": "on_leave", "effective_on": "2026-09-30"},
        ),
    ],
)
def test_cross_organisation_employee_is_hidden(
    client: TestClient, method: str, path: str, json: dict | None
) -> None:
    response = client.request(method, path, headers={"X-Dev-User": "marion.teague"}, json=json)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

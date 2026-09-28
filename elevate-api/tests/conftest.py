import copy

import pytest
from fastapi.testclient import TestClient

from app.audit import access_log
from app.main import api
from app.store import store

ORIGINAL_EMPLOYEES = copy.deepcopy(store.employees)
ORIGINAL_ORG_UNITS = copy.deepcopy(store.org_units)
ORIGINAL_ROLE_ANCHORS = copy.deepcopy(store.role_anchors)


@pytest.fixture(autouse=True)
def reset_store() -> None:
    store.employees[:] = copy.deepcopy(ORIGINAL_EMPLOYEES)
    store.org_units[:] = copy.deepcopy(ORIGINAL_ORG_UNITS)
    store.role_anchors[:] = copy.deepcopy(ORIGINAL_ROLE_ANCHORS)
    access_log.clear()
    store.rebuild_indexes()


@pytest.fixture
def client() -> TestClient:
    return TestClient(api, raise_server_exceptions=False)

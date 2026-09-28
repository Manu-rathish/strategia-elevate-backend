import copy

import pytest
from fastapi.testclient import TestClient

from app.main import api
from app.store import store

ORIGINAL_EMPLOYEES = copy.deepcopy(store.employees)


@pytest.fixture(autouse=True)
def reset_store() -> None:
    store.employees[:] = copy.deepcopy(ORIGINAL_EMPLOYEES)
    store.rebuild_indexes()


@pytest.fixture
def client() -> TestClient:
    return TestClient(api, raise_server_exceptions=False)

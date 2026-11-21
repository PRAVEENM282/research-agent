from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
import src.main as main_module
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(main_module, "init_db", AsyncMock())
    monkeypatch.setattr(main_module, "close_engines", AsyncMock())
    monkeypatch.setattr(main_module, "persist_demo_task", lambda: None)
    with TestClient(main_module.app) as test_client:
        yield test_client

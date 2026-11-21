"""tests/conftest.py — Fixtures estándar para Pytest (FastAPI + Clean Architecture).

Las dependencias de testing (FastAPI y httpx2) son obligatorias: si faltan, la
importación de este módulo falla y pytest se detiene con error. No se saltan
tests en silencio.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
def sync_client() -> Generator[Any, None, None]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[Any, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

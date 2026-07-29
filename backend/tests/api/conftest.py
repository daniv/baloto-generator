"""Pytest fixtures specific to API (endpoint) tests."""

from typing import TYPE_CHECKING

import pytest
from backend.app.db.session import get_db
from backend.app.main import create_app
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from collections.abc import Generator
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="function")
def client(db_session: AsyncSession) -> Generator[TestClient]:
    """
    Provide a TestClient whose DB dependency is bound to the isolated test session.

    :param db_session: The per-test, rolled-back-on-teardown async session
        provided by the root conftest.
    :return: A :class:`TestClient` ready to make requests against the app.
    """
    app = create_app()

    async def _override_get_db() -> AsyncSession:
        return db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

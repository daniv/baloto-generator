"""Pytest fixtures specific to API (endpoint) tests."""

from typing import TYPE_CHECKING, Any

import pytest
from app.db.session import get_db
from app.main import create_app
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator

    from sqlalchemy.ext.asyncio import AsyncSession

type RunAsync = Callable[[Coroutine[Any, Any, Any]], Any]


@pytest.fixture
def client(db_session: AsyncSession, run_async: RunAsync) -> Generator[AsyncClient]:
    """
    Provide an async test client wired to the isolated test session.

    Uses ``httpx.AsyncClient`` with an in-process ``ASGITransport`` instead
    of Starlette's ``TestClient``: ``TestClient`` runs the app on its own
    internal event loop, which cannot safely share the connection held by
    ``db_session``. Requests made through this client run coroutines that
    must be driven with ``run_async`` (the same shared loop used to build
    ``db_session``), keeping everything on one loop.

    :param db_session: The per-test, rolled-back-on-teardown async session
        provided by the root conftest.
    :param run_async: The helper that runs coroutines on the shared loop.
    :return: An :class:`httpx.AsyncClient` ready to make requests.
    """
    app = create_app()

    async def _override_get_db() -> AsyncSession:
        return db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    test_client = AsyncClient(transport=transport, base_url="http://testserver")

    yield test_client

    run_async(test_client.aclose())
    app.dependency_overrides.clear()

"""
Shared pytest fixtures for database-backed tests.

Provides a real, disposable PostgreSQL instance via Testcontainers, an
async SQLAlchemy engine bound to it, and a per-test isolated session
that rolls back after each test so no test leaks data into the next one.

All async code in this file, in dependent conftest modules, and in test
bodies themselves runs on a single, session-scoped event loop (see
:func:`run_async`) instead of a fresh loop per call. An async database
connection is bound to the event loop that was running when it was
created and cannot be driven from a different one -- including from
Starlette's ``TestClient``, which runs its own internal loop. Using one
shared loop for everything in the test session avoids that entirely.
"""

import asyncio
from typing import TYPE_CHECKING, Any

import pytest
from app.models import Base
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator

type RunAsync = Callable[[Coroutine[Any, Any, Any]], Any]


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """
    Provide a single event loop shared by every fixture and test in the session.

    :return: The event loop used by :func:`run_async` for the whole session.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def run_async(event_loop: asyncio.AbstractEventLoop) -> RunAsync:
    """
    Provide a helper that runs a coroutine on the session's shared event loop.

    :param event_loop: The session-scoped event loop.
    :return: A callable that runs a coroutine to completion on that loop.
    """

    def _run[T](coroutine: Coroutine[Any, Any, T]) -> T:
        return event_loop.run_until_complete(coroutine)

    return _run


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """
    Start a disposable PostgreSQL container for the whole test session.

    :return: A running :class:`PostgresContainer`, torn down automatically
        once every test in the session has finished.
    """
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="session")
def db_engine(postgres_container: PostgresContainer, run_async: RunAsync) -> Generator[AsyncEngine]:
    """
    Create the async engine used by tests and create all tables on it.

    :param postgres_container: The running Postgres test container.
    :param run_async: The helper that runs coroutines on the shared loop.
    :return: An :class:`AsyncEngine` connected to the test database.
    """
    engine = create_async_engine(postgres_container.get_connection_url(), poolclass=NullPool)

    async def _create_tables() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    run_async(_create_tables())

    yield engine

    run_async(engine.dispose())


@pytest.fixture
def db_session(db_engine: AsyncEngine, run_async: RunAsync) -> Generator[AsyncSession]:
    """
    Provide a database session isolated to a single test.

    Opens a connection and an outer transaction before the test runs, and
    binds an :class:`AsyncSession` to that connection using
    ``join_transaction_mode="create_savepoint"`` so that even if the code
    under test calls ``session.commit()``, the outer transaction is left
    intact. The outer transaction is rolled back after the test, so no
    data written during the test persists.

    :param db_engine: The session-scoped async engine.
    :param run_async: The helper that runs coroutines on the shared loop.
    :return: An :class:`AsyncSession` scoped to a transaction that is
        rolled back once the test completes.
    """

    async def _setup() -> tuple[Any, Any, AsyncSession]:
        connection = await db_engine.connect()
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint")
        return connection, transaction, session

    connection, transaction, session = run_async(_setup())

    yield session

    async def _teardown() -> None:
        await session.close()
        await transaction.rollback()
        await connection.close()

    run_async(_teardown())

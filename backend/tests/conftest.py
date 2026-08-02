"""
Shared pytest fixtures for database-backed tests.

Provides a real, disposable PostgreSQL instance via Testcontainers, an
async SQLAlchemy engine bound to it, and a per-test isolated session
that rolls back after each test so no test leaks data into the next one.
"""

import asyncio
from typing import TYPE_CHECKING, Any

import pytest
from app.models import Base
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator


@pytest.hookimpl
def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Add command-line options for pytest.

    :param parser: Pytest command-line parser.
    :return: None
    """
    group = parser.getgroup("baloto-generator", "Baloto Generator custom options")
    group.addoption(
        "--game",
        action="store",
        default=None,
        choices=["miloto", "baloto", "revancha"],
        help="Run tests on the specified game. Options: miloto, baloto, revancha.",
    )


def run_async[T](awaitable: Awaitable[T]) -> T:
    """
    Run an async coroutine from synchronous test code.

    Each call executes the coroutine in a brand-new event loop via
    :func:`asyncio.run`. The async engine used alongside this helper must
    be configured with ``poolclass=NullPool`` so that no database
    connection is ever reused across two different event loops.

    :param coroutine: The coroutine object to execute.
    :return: The value returned by the coroutine.
    """

    async def execute() -> T:
        return await awaitable

    return asyncio.run(execute())


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
def db_engine(postgres_container: PostgresContainer) -> Generator[AsyncEngine]:
    """
    Create the async engine used by tests and create all tables on it.

    ``NullPool`` is required here: fixtures bridge async code into sync
    pytest fixtures by opening a new event loop per call (see
    :func:`run_async`), and a pooled connection created in one event loop
    cannot be reused safely in another.

    :param postgres_container: The running Postgres test container.
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
def db_session(db_engine: AsyncEngine) -> Generator[AsyncSession]:
    """
    Provide a database session isolated to a single test.

    Opens a connection and an outer transaction before the test runs, and
    binds an :class:`AsyncSession` to that connection using
    ``join_transaction_mode="create_savepoint"`` so that even if the code
    under test calls ``session.commit()``, the outer transaction is left
    intact. The outer transaction is rolled back after the test, so no
    data written during the test persists.

    :param db_engine: The session-scoped async engine.
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

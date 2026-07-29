"""
Async database engine and session dependency for FastAPI.

Defines the SQLAlchemy async engine used by the application and the
``get_db`` dependency that endpoints use via ``Depends`` to obtain a
request-scoped :class:`AsyncSession`.
"""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.app_settings import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


engine = create_async_engine(str(settings.db_settings.pg_dsn))

async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Yield a request-scoped database session.

    Used as a FastAPI dependency via ``Depends(get_db)``. The session is
    closed automatically once the request finishes.

    :return: An async generator yielding a single :class:`AsyncSession`.
    """
    async with async_session_maker() as session:
        yield session

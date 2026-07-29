"""CRUD operations for Miloto results.

Read-only data access functions for the ``miloto_results`` table. These
functions return ORM objects; converting them to API response schemas is
the responsibility of the router layer.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.miloto_db import MilotoResult


async def get_miloto_results_page(db: AsyncSession, page: int, size: int) -> tuple[list[MilotoResult], int]:
    """Fetch one page of Miloto results, most recent draw first.

    :param db: The active database session.
    :param page: The 1-indexed page number to fetch.
    :param size: The number of results per page.
    :return: A tuple of (results for this page, total number of results).
    """
    offset = (page - 1) * size

    total_stmt = select(func.count()).select_from(MilotoResult)
    total = (await db.execute(total_stmt)).scalar_one()

    results_stmt = select(MilotoResult).order_by(MilotoResult.game_date.desc()).offset(offset).limit(size)
    results = (await db.execute(results_stmt)).scalars().all()

    return list(results), total


async def get_miloto_result_by_game_id(db: AsyncSession, game_id: int) -> MilotoResult | None:
    """Fetch a single Miloto result by its game id.

    :param db: The active database session.
    :param game_id: The game id (draw number) to look up.
    :return: The matching :class:`MilotoResult`, or ``None`` if not found.
    """
    stmt = select(MilotoResult).where(MilotoResult.game_id == game_id)
    return (await db.execute(stmt)).scalar_one_or_none()
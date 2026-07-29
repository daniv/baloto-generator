"""API routes for Miloto results."""

import math
from typing import TYPE_CHECKING, Annotated

from backend.app.crud.miloto import get_miloto_result_by_game_id, get_miloto_results_page
from backend.app.db.session import get_db
from backend.app.schemas.miloto import MilotoResultSchema
from backend.app.schemas.pagination import PaginatedResponse
from fastapi import APIRouter, Depends, HTTPException, Query

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/miloto", tags=["miloto"])


@router.get("", response_model=PaginatedResponse[MilotoResultSchema])
async def list_miloto_results(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 15,
) -> PaginatedResponse[MilotoResultSchema]:
    """
    List Miloto results, most recent draw first, paginated.

    :param db: The request-scoped database session.
    :param page: The 1-indexed page number to fetch.
    :param size: The number of results per page.
    :return: A page of Miloto results wrapped in pagination metadata.
    """
    results, total = await get_miloto_results_page(db, page=page, size=size)
    pages = math.ceil(total / size) if total else 0

    return PaginatedResponse[MilotoResultSchema](
        items=[MilotoResultSchema.model_validate(result) for result in results],
        page=page,
        size=size,
        total=total,
        pages=pages,
    )


@router.get("/{game_id}", response_model=MilotoResultSchema)
async def get_miloto_result(
    game_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MilotoResultSchema:
    """
    Fetch a single Miloto result by its game id.

    :param game_id: The game id (draw number) to look up.
    :param db: The request-scoped database session.
    :raises HTTPException: If no result exists for the given game id.
    :return: The matching Miloto result.
    """
    result = await get_miloto_result_by_game_id(db, game_id=game_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Miloto result with game_id {game_id!r} not found.")

    return MilotoResultSchema.model_validate(result)

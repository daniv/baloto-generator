"""
Verify Miloto API endpoints for retrieving stored draw results.

The module covers fetching a single Miloto result by its game_id, confirming
that a result inserted through the database session is correctly returned
by the API, including nested prize-detail fields such as hits_2.
"""

from datetime import date
from typing import TYPE_CHECKING, Any

from app.models.miloto_db import MilotoResult

if TYPE_CHECKING:
    from collections.abc import Callable

    from httpx import AsyncClient, Response
    from sqlalchemy.ext.asyncio import AsyncSession


SAMPLE_MILOTO_RESULT: dict[str, Any] = {
    "game_id": 1,
    "game_date": date(2023, 10, 20),
    "num_1": 10,
    "num_2": 11,
    "num_3": 18,
    "num_4": 32,
    "num_5": 38,
    "accumulated": 120000000,
    "hits_2": {"prize_for_winner": 4000, "winners": 1261},
    "hits_3": {"prize_for_winner": 46300, "winners": 112},
    "hits_4": {"prize_for_winner": 588750, "winners": 5},
    "hits_5": None,
}


def test_get_miloto_result_by_game_id(
    client: AsyncClient,
    db_session: AsyncSession,
    run_async: Callable[..., Any],
) -> None:
    """
    GET /miloto/{game_id} returns the stored result for an existing game_id.

    :param client: The async test client, wired to the isolated test session.
    :param db_session: The per-test, rolled-back-on-teardown async session.
    :param run_async: The helper that runs coroutines on the shared loop.
    """

    async def _seed_and_call() -> Response:
        db_session.add(MilotoResult(**SAMPLE_MILOTO_RESULT))
        await db_session.commit()
        return await client.get(f"/miloto/{SAMPLE_MILOTO_RESULT['game_id']}")

    response = run_async(_seed_and_call())

    assert response.status_code == 200, response.json()

    body = response.json()
    assert body["game_id"] == SAMPLE_MILOTO_RESULT["game_id"]
    assert body["num_1"] == SAMPLE_MILOTO_RESULT["num_1"]
    assert body["num_5"] == SAMPLE_MILOTO_RESULT["num_5"]
    assert body["accumulated"] == SAMPLE_MILOTO_RESULT["accumulated"]
    assert body["hits_2"]["winners"] == SAMPLE_MILOTO_RESULT["hits_2"]["winners"]

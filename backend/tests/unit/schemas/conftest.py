from typing import TYPE_CHECKING, Any

import pytest
from backend.app.config.app_settings import settings
from backend.app.schemas.baloto import BalotoResultSchema, RevanchaResultSchema
from backend.app.schemas.base import ResultDetailsSchema
from backend.app.schemas.miloto import MilotoResultSchema

if TYPE_CHECKING:
    from pytest import FixtureRequest
    from collections.abc import Callable
    from datetime import date
    type BalotoResult = BalotoResultSchema | RevanchaResultSchema


@pytest.fixture(name="br_factory", scope="module", params=["revancha", "baloto"])
def baloto_revancha_factory(request: FixtureRequest) -> Callable[..., BalotoResult]:

    def _factory(
        gid: int, dte: date | str, n1: int, n2: int, n3: int, n4: int, n5: int, ba: int, acc: int | None = None
    ) -> BalotoResult:
        accumulated = settings.baloto_settings.baloto_min_jackpot if acc is None else acc
        schema: dict[str, Any] = {
            "game_id": gid,
            "game_date": dte,
            "num_1": n1,
            "num_2": n2,
            "num_3": n3,
            "num_4": n4,
            "num_5": n5,
            "balota": ba,
            "accumulated": accumulated,
        }
        if request.param == "baloto":
            return BalotoResultSchema(**schema)
        return RevanchaResultSchema(**schema)

    return _factory


@pytest.fixture(name="m_factory", scope="module")
def miloto_factory() -> Callable[..., MilotoResultSchema]:

    def _factory(
        gid: int,
        dte: date | str,
        n1: int,
        n2: int,
        n3: int,
        n4: int,
        n5: int,
        acc: int = settings.baloto_settings.miloto_min_jackpot,
    ) -> MilotoResultSchema:
        schema: dict[str, Any] = {
            "game_id": gid,
            "game_date": dte,
            "num_1": n1,
            "num_2": n2,
            "num_3": n3,
            "num_4": n4,
            "num_5": n5,
            "accumulated": acc,
        }
        return MilotoResultSchema(**schema)

    return _factory


@pytest.fixture(scope="module")
def valid_hit_details() -> ResultDetailsSchema:
    return ResultDetailsSchema(prize_for_winner=50_000, winners=10)

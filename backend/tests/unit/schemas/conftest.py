"""
Provide reusable pytest fixtures for lottery schema unit tests.

The module builds valid Baloto, Revancha, and MiLoto schema instances with
customizable values. These factories keep test setup consistent, reduce repeated
construction logic, and make validation scenarios easier to express and maintain.
"""

from typing import TYPE_CHECKING, Any

import pytest
from app.config.app_settings import settings
from app.schemas.baloto import BalotoResultSchema, RevanchaResultSchema
from app.schemas.miloto import MilotoResultSchema

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date

    type BalotoResult = BalotoResultSchema | RevanchaResultSchema


@pytest.fixture(name="br_factory", scope="module", params=["revancha", "baloto"])
def baloto_revancha_factory(request: pytest.FixtureRequest) -> Callable[..., BalotoResult]:
    """
    Create a Callable[..., BalotoResult] fixture for parameterized factory tests.

    The parameterized factory returns a RevanchaResultSchema instance on the
    first iteration and a BalotoResultSchema instance afterward, allowing the
    same tests to validate both schemas.
    """

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
    """Create a Callable[..., MilotoResultSchema] fixture so a test can parameterize the factory."""

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

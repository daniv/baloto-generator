"""
Expose the public lottery result-extraction API.

This package exports the supported Playwright page objects, the shared
extraction protocol, and the utilities used to retrieve validated result HTML.
"""

from typing import TYPE_CHECKING, Protocol

from app.utils.playwright_utils.baloto_page import BalotoPage, RevanchaPage
from app.utils.playwright_utils.html_loader import DrawPageNotFoundError, get_html
from app.utils.playwright_utils.miloto_page import MilotoPage

if TYPE_CHECKING:
    from app.schemas.base import ResultDetailsSchema


class ResultPage(Protocol):
    """
    Define the information required from a lottery result page.

    The protocol allows services to process ``BalotoPage``, ``RevanchaPage``,
    and ``MilotoPage`` without depending on their concrete implementations.

    Compatible classes do not need to inherit from this protocol explicitly.
    They only need to provide methods with matching signatures.
    """

    async def get_game_id(self) -> int:
        """
        Extract the identifier displayed for the loaded lottery draw.

        :return: Normalized draw identifier.
        """
        ...

    async def get_game_date(self) -> str:
        """
        Extract the date displayed for the loaded lottery draw.

        The value is returned exactly as presented by the website so date
        parsing remains the responsibility of the consuming schema or service.

        :return: Displayed draw date in Spanish.
        """
        ...

    async def get_winner_numbers(self) -> list[int]:
        """
        Extract the regular winning numbers from the loaded lottery draw.

        :return: Winning numbers in their displayed order.
        """
        ...

    async def get_accumulated_prize(self) -> int:
        """
        Extract the accumulated prize and normalize it to Colombian pesos.

        :return: Accumulated prize expressed as an integer number of pesos.
        """
        ...

    async def get_details(self) -> dict[str, ResultDetailsSchema]:
        """
        Extract payout information for categories with registered winners.

        :return: Mapping of normalized hit categories to payout details.
        """
        ...

    async def validate_draw_id(self) -> None:
        """
        Verify that the loaded HTML belongs to the expected lottery draw.

        :raises ValueError: If the identifier extracted from the document does not
            match the identifier configured for the page object.
        """
        ...

    async def get_detail(
        self,
        hits: str,
    ) -> ResultDetailsSchema | None:
        """
        Return payout information for one requested hit category.

        :param hits: Game-specific hit category to retrieve.
        :return: Payout information, or ``None`` when the category has no winners.
        """
        ...


__all__ = [
    "BalotoPage",
    "DrawPageNotFoundError",
    "MilotoPage",
    "ResultPage",
    "RevanchaPage",
    "get_html",
]

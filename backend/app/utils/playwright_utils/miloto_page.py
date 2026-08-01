"""
Provide the page object for an individual MiLoto draw result.

This module defines ``MilotoPage``, an asynchronous Playwright page object
that extracts deterministic data from a MiLoto result document already loaded
into a Playwright page.

The page object supports extraction of:

- The draw identifier.
- The displayed draw date.
- The five winning numbers.
- The accumulated prize.
- All prize-distribution categories.
- One requested prize-distribution category.

The object does not navigate or download HTML. Loading the result document
remains the responsibility of the calling service or test fixture.
"""

import re
from typing import TYPE_CHECKING, Literal, cast

from pydantic import TypeAdapter

from app.config.app_settings import settings
from app.schemas.base import ResultDetailsSchema
from app.utils.playwright_utils.base_page import (
    BasePage,
    parse_localized_match_to_int,
    parse_millions_to_pesos,
    validate_draw_id,
)

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page
    from pydantic import HttpUrl


type MilotoHits = Literal["2", "3", "4", "5"]

_MILOTO_HITS_ADAPTER: TypeAdapter[MilotoHits] = TypeAdapter(MilotoHits)


class MilotoPage(BasePage):
    """
    Represent the loaded result document for one MiLoto draw.

    Each instance receives a Playwright page whose HTML has already been loaded
    and a positive expected draw identifier. Public extraction methods validate
    the required DOM structure before reading text so malformed documents fail
    immediately with meaningful ``ValueError`` exceptions instead of waiting
    for Playwright locator timeouts.

    The class satisfies the shared ``ResultPage`` protocol structurally without
    inheriting from it explicitly.
    """

    _WINNING_NUMBERS_COUNT = 5
    _DETAILS_COUNT = 4

    _GAME_ID_PATTERN = re.compile(
        r"^SORTEO\s+#?(\d{1,3}(?:\.\d{3})*)$",
        re.IGNORECASE,
    )
    _GAME_DATE_PATTERN = re.compile(
        r"^\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+\s+de\s+\d{4}$",
        re.IGNORECASE,
    )
    _ACCUMULATED_PRIZE_PATTERN = re.compile(
        r"ACUMULADO DEL SORTEO:\s*\$([\d.]+)\s+MILLONES",
        re.IGNORECASE,
    )
    _INTEGER_PATTERN = re.compile(r"(\d+(?:\.\d{3})*)")

    def __init__(self, page: Page, draw_id: int) -> None:
        """
        Initialize a MiLoto result-page extractor.

        :param page: Playwright page containing the MiLoto result HTML.
        :param draw_id: Positive draw identifier expected in the loaded HTML.
        :raises ValueError: If ``draw_id`` is not greater than zero.
        """
        if draw_id <= 0:
            error_message = "draw_id must be greater than zero."
            raise ValueError(error_message)

        super().__init__(page)
        self._draw_id = draw_id

    @property
    def result_url(self) -> HttpUrl:
        """
        Return the configured MiLoto results base URL.

        The URL is metadata available to production services that retrieve HTML.
        This page object does not navigate to it directly.

        :return: Configured MiLoto results URL.
        """
        return settings.baloto_settings.miloto_baseurl

    @property
    def game_name(self) -> str:
        """
        Return the canonical MiLoto game name.

        :return: Human-readable MiLoto game name.
        """
        return "Miloto"

    def _game_id(self) -> Locator:
        """
        Return the element containing the MiLoto draw identifier.

        :return: Locator matching identifiers such as ``SORTEO #579``.
        """
        return self._page.get_by_text(self._GAME_ID_PATTERN)

    def _game_date(self) -> Locator:
        """
        Return the element containing the displayed MiLoto draw date.

        :return: Locator matching a Spanish result date.
        """
        return self._page.get_by_text(self._GAME_DATE_PATTERN)

    def _winner_numbers(self) -> Locator:
        """
        Return the winning-number elements scoped to the result container.

        :return: Locator containing the five MiLoto winning-number elements.
        """
        result_container = self._page.locator(
            "div.text-center.mt-5.mb-5",
        ).filter(
            has_text=re.compile(
                r"ACUMULADO DEL SORTEO",
                re.IGNORECASE,
            ),
        )

        return result_container.locator(".yellow-ball")

    def _accumulated_prize(self) -> Locator:
        """
        Return the element containing the accumulated MiLoto prize.

        :return: Locator containing the accumulated-prize text.
        """
        return self._page.get_by_text(
            self._ACCUMULATED_PRIZE_PATTERN,
        )

    def _detail_cards(self) -> Locator:
        """
        Return the four MiLoto prize-category cards.

        :return: Locator containing cards with an ``aciertos`` section.
        """
        return self._page.locator(
            "div.mt-4.bg-white.rounded",
        ).filter(
            has=self._page.locator(".aciertos"),
        )

    @staticmethod
    async def _require_exact_count(
        locator: Locator,
        expected_count: int,
        field_name: str,
    ) -> None:
        """
        Validate the exact number of nodes required by an extraction operation.

        ``Locator.count`` inspects the current DOM without waiting for elements
        to appear. This allows intentionally malformed test documents to fail
        immediately instead of reaching Playwright's default timeout.

        :param locator: Locator whose current number of matches is validated.
        :param expected_count: Exact number of required matching nodes.
        :param field_name: Human-readable field included in validation errors.
        :raises ValueError: If the actual count differs from ``expected_count``.
        """
        actual_count = await locator.count()

        if actual_count != expected_count:
            error_message = (
                f"Invalid MiLoto {field_name} structure: expected {expected_count} node(s), found {actual_count}."
            )
            raise ValueError(error_message)

    async def _get_required_text(
        self,
        locator: Locator,
        field_name: str,
    ) -> str:
        """
        Return text from exactly one required DOM node.

        :param locator: Locator expected to match one node.
        :param field_name: Human-readable field included in validation errors.
        :return: Stripped inner text from the required node.
        :raises ValueError: If the locator does not match exactly one node.
        """
        await self._require_exact_count(
            locator,
            expected_count=1,
            field_name=field_name,
        )
        return await self.get_text(locator)

    def _extract_detail_integer(
        self,
        value: str,
        field_name: str,
    ) -> int:
        """
        Extract a Spanish-formatted integer from a MiLoto detail value.

        Currency symbols, whitespace, line breaks, and surrounding text are
        ignored. For example, ``"$3.996.400"`` becomes ``3_996_400``.

        :param value: Raw text extracted from a prize-detail node.
        :param field_name: Field name included in validation errors.
        :return: Parsed integer value.
        :raises ValueError: If the supplied text contains no valid integer.
        """
        match = self._INTEGER_PATTERN.search(value)

        if match is None:
            error_message = f"Could not extract the MiLoto {field_name} value from: {value!r}"
            raise ValueError(error_message)

        return parse_localized_match_to_int(match)

    async def _get_detail_category(self, card: Locator) -> MilotoHits:
        """
        Extract and validate the hit category displayed by one detail card.

        :param card: Locator representing one MiLoto prize-category card.
        :return: Valid MiLoto hit category.
        :raises ValueError: If the category node is missing, duplicated, or
            contains an unsupported value.
        """
        category_locator = card.locator(".fs-aciertos")
        category = await self._get_required_text(
            category_locator,
            "detail category",
        )

        if category not in {"2", "3", "4", "5"}:
            error_message = f"Unsupported MiLoto hit category found in the result document: {category!r}."
            raise ValueError(error_message)

        return cast("MilotoHits", category)

    async def _parse_detail_card(
        self,
        card: Locator,
    ) -> tuple[MilotoHits, ResultDetailsSchema] | None:
        """
        Convert one MiLoto prize card into payout information.

        A category with zero registered winners returns ``None``. The category
        must still exist and expose its complete DOM structure; only its payout
        result is optional.

        :param card: Locator representing one MiLoto prize-category card.
        :return: Category and payout details, or ``None`` for zero winners.
        :raises ValueError: If any required card node is missing, duplicated,
            unsupported, or contains invalid numeric data.
        """
        category = await self._get_detail_category(card)

        payout_section = card.locator(
            "div.light-blue",
        ).filter(
            has_text=re.compile(
                r"Premio por ganador",
                re.IGNORECASE,
            ),
        )
        await self._require_exact_count(
            payout_section,
            expected_count=1,
            field_name=f"category {category} payout section",
        )

        highlighted_values = payout_section.locator("span.pink-light")
        await self._require_exact_count(
            highlighted_values,
            expected_count=2,
            field_name=f"category {category} highlighted values",
        )

        prize_text = await self.get_text(highlighted_values.nth(0))
        winners_text = await self.get_text(highlighted_values.nth(1))

        winners = self._extract_detail_integer(
            winners_text,
            "winner count",
        )

        if winners == 0:
            return None

        prize_for_winner = self._extract_detail_integer(
            prize_text,
            "prize per winner",
        )

        return category, ResultDetailsSchema(
            prize_for_winner=prize_for_winner,
            winners=winners,
        )

    async def _get_validated_detail_cards(self) -> list[Locator]:
        """
        Return the complete validated collection of MiLoto detail cards.

        :return: Four detail-card locators.
        :raises ValueError: If the result document does not contain exactly four
            prize-category cards.
        """
        cards_locator = self._detail_cards()
        await self._require_exact_count(
            cards_locator,
            expected_count=self._DETAILS_COUNT,
            field_name="prize-category cards",
        )
        return await cards_locator.all()

    async def validate_draw_id(self) -> None:
        """
        Verify that the loaded HTML belongs to the configured MiLoto draw.

        :raises ValueError: If the displayed and expected identifiers differ.
        """
        actual_draw_id = await self.get_game_id()
        validate_draw_id(self._draw_id, actual_draw_id)

    async def get_game_id(self) -> int:
        """
        Extract and normalize the loaded MiLoto draw identifier.

        Values such as ``SORTEO #1.000`` are normalized to ``1000``.

        :return: Parsed MiLoto draw identifier.
        :raises ValueError: If the identifier node is missing, duplicated, or
            contains an invalid identifier.
        """
        text = await self._get_required_text(
            self._game_id(),
            "draw identifier",
        )
        match = self._GAME_ID_PATTERN.fullmatch(text)

        if match is None:
            error_message = f"Could not extract the MiLoto game identifier from: {text!r}"
            raise ValueError(error_message)

        return parse_localized_match_to_int(match)

    async def get_game_date(self) -> str:
        """
        Extract the date exactly as displayed in the MiLoto result document.

        Parsing or conversion into ``datetime.date`` remains the responsibility
        of the schema or service that consumes this extracted value.

        :return: Spanish date text such as ``28 de Julio de 2026``.
        :raises ValueError: If the date node is missing or duplicated.
        """
        return await self._get_required_text(
            self._game_date(),
            "draw date",
        )

    async def get_winner_numbers(self) -> list[int]:
        """
        Extract the five winning numbers in their displayed order.

        Values such as ``"01"`` are normalized to integers such as ``1``.

        :return: Five MiLoto winning numbers.
        :raises ValueError: If the number of nodes is invalid or any displayed
            value cannot be converted to an integer.
        """
        winner_numbers = self._winner_numbers()
        await self._require_exact_count(
            winner_numbers,
            expected_count=self._WINNING_NUMBERS_COUNT,
            field_name="winning numbers",
        )

        number_texts = await winner_numbers.all_inner_texts()

        try:
            return [int(value.strip()) for value in number_texts]
        except ValueError as error:
            error_message = f"Invalid MiLoto winning-number values: {number_texts!r}"
            raise ValueError(error_message) from error

    async def get_accumulated_prize(self) -> int:
        """
        Extract the accumulated prize and normalize it to Colombian pesos.

        A displayed value such as ``$230 MILLONES`` is converted into
        ``230_000_000``.

        :return: Accumulated prize expressed in Colombian pesos.
        :raises ValueError: If the node is missing, duplicated, or its value
            cannot be parsed.
        """
        text = await self._get_required_text(
            self._accumulated_prize(),
            "accumulated prize",
        )
        match = self._ACCUMULATED_PRIZE_PATTERN.fullmatch(text)

        if match is None:
            error_message = f"Could not extract the MiLoto accumulated prize from: {text!r}"
            raise ValueError(error_message)

        return parse_millions_to_pesos(match.group(1))

    async def get_detail(
        self,
        hits: str,
    ) -> ResultDetailsSchema | None:
        """
        Return payout information for one requested MiLoto hit category.

        The supplied category is validated as one of the supported MiLoto values:
        ``"2"``, ``"3"``, ``"4"``, or ``"5"``. The result document must contain
        all four category cards.

        ``None`` is returned only when the requested category exists and reports
        zero winners. A missing category or malformed card is treated as invalid
        result HTML.

        :param hits: MiLoto hit category to retrieve.
        :return: Payout information, or ``None`` when the category has no
            registered winners.
        :raises ValidationError: If ``hits`` is not a supported MiLoto category.
        :raises ValueError: If the expected category card is missing or contains
            incomplete or invalid data.
        """
        validated_hits = _MILOTO_HITS_ADAPTER.validate_python(hits)
        cards = await self._get_validated_detail_cards()

        for card in cards:
            category = await self._get_detail_category(card)

            if category != validated_hits:
                continue

            parsed_detail = await self._parse_detail_card(card)

            if parsed_detail is None:
                return None

            return parsed_detail[1]

        error_message = f"The MiLoto result document does not contain the expected hit category {validated_hits!r}."
        raise ValueError(error_message)

    async def get_details(self) -> dict[str, ResultDetailsSchema]:
        """
        Extract payout details for all MiLoto categories with winners.

        The result document must contain the four expected categories:
        ``2``, ``3``, ``4``, and ``5``. Categories whose winner count is zero
        are validated but omitted from the returned dictionary.

        :return: Mapping of awarded hit categories to payout information.
        :raises ValueError: If the document structure is incomplete, contains
            unsupported or duplicated categories, or has invalid numeric data.
        """
        cards = await self._get_validated_detail_cards()
        details: dict[str, ResultDetailsSchema] = {}
        discovered_categories: set[MilotoHits] = set()

        for card in cards:
            category = await self._get_detail_category(card)

            if category in discovered_categories:
                error_message = f"Duplicate MiLoto hit category found in the result document: {category!r}."
                raise ValueError(error_message)

            discovered_categories.add(category)
            parsed_detail = await self._parse_detail_card(card)

            if parsed_detail is None:
                continue

            parsed_category, result_schema = parsed_detail
            details[parsed_category] = result_schema

        expected_categories: set[MilotoHits] = {"2", "3", "4", "5"}

        if discovered_categories != expected_categories:
            missing_categories = sorted(
                expected_categories.difference(discovered_categories),
            )
            error_message = f"The MiLoto result document is missing expected hit categories: {missing_categories!r}."
            raise ValueError(error_message)

        return details

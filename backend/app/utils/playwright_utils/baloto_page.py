"""
Provide page objects for individual Baloto and Revancha draw results.

This module defines the shared ``_BalotoResultPage`` implementation together
with the concrete ``BalotoPage`` and ``RevanchaPage`` classes.

Both games expose the same result-document structure and prize categories, so
the shared class provides extraction for:

- The draw identifier.
- The displayed draw date.
- The five regular winning numbers.
- The red superball.
- The accumulated prize.
- All awarded prize categories.
- One requested prize category.

Every public extraction operation automatically validates that the loaded
document belongs to the concrete game before reading result data.
"""

import re
from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar, Literal

from pydantic import TypeAdapter

from app.config.app_settings import settings
from app.schemas.base import ResultDetailsSchema
from app.utils.playwright_utils.base_page import (
    BasePage,
    DetailsColumnIndexes,
    normalize_baloto_hits_key,
    parse_localized_match_to_int,
    parse_millions_to_pesos,
    validate_draw_id,
)

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page
    from pydantic import HttpUrl


type BalotoHits = Literal[
    "SB",
    "2+SB",
    "3",
    "3+SB",
    "4",
    "4+SB",
    "5",
    "5+SB",
]

_BALOTO_HITS_ADAPTER: TypeAdapter[BalotoHits] = TypeAdapter(BalotoHits)


class _BalotoResultPage(BasePage):
    """
    Represent the shared result structure used by Baloto and Revancha.

    Each instance receives a Playwright page whose result HTML is already
    loaded and a positive expected draw identifier.

    The concrete game identity is validated automatically before any public
    extraction operation. A successful validation is cached for the lifetime
    of the page object, preventing repeated DOM checks.

    Required DOM nodes are counted before their text is accessed. Malformed
    static fixtures therefore fail immediately with meaningful ``ValueError``
    exceptions instead of waiting for Playwright timeouts.
    """

    _WINNING_NUMBERS_COUNT = 5
    _DETAILS_COUNT = 8
    _DETAILS_COLUMN_COUNT = 4

    _EXPECTED_HITS: ClassVar[set[BalotoHits]] = {
        "SB",
        "2+SB",
        "3",
        "3+SB",
        "4",
        "4+SB",
        "5",
        "5+SB",
    }

    _GAME_ID_PATTERN = re.compile(
        r"^SORTEO\s+(\d{1,3}(?:\.\d{3})*)$",
        re.IGNORECASE,
    )
    _GAME_DATE_PATTERN = re.compile(
        r"^\s*\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+\s+de\s+\d{4}\s*$",
        re.IGNORECASE,
    )
    _ACCUMULATED_PRIZE_PATTERN = re.compile(
        r"ACUMULADO DEL SORTEO:\s*\$([\d.]+)\s+MILLONES",
        re.IGNORECASE,
    )
    _TABLE_INTEGER_PATTERN = re.compile(
        r"(\d+(?:\.\d{3})*)",
    )

    def __init__(self, page: Page, draw_id: int) -> None:
        """
        Initialize a Baloto-style result-page extractor.

        Game validation cannot run directly from ``__init__`` because it
        requires asynchronous Playwright operations. Instead, every public
        extraction method invokes ``_ensure_game_validated`` before accessing
        result data.

        :param page: Playwright page containing the result HTML.
        :param draw_id: Positive draw identifier expected in the loaded HTML.
        :raises ValueError: If ``draw_id`` is not greater than zero.
        """
        if draw_id <= 0:
            error_message = "draw_id must be greater than zero."
            raise ValueError(error_message)

        super().__init__(page)
        self._draw_id = draw_id
        self._game_validated = False

    @property
    @abstractmethod
    def result_url(self) -> HttpUrl:
        """
        Return the configured results URL for the concrete game.

        :return: Configured Baloto or Revancha results URL.
        """

    @property
    @abstractmethod
    def game_name(self) -> str:
        """
        Return the human-readable name of the concrete game.

        :return: ``"Baloto"`` or ``"Revancha"``.
        """

    @abstractmethod
    async def validate_game(self) -> None:
        """
        Verify that the loaded HTML belongs to the concrete game.

        Concrete implementations must inspect the DOM directly. They must not
        invoke public extraction methods because those methods trigger automatic
        game validation and would create recursive calls.

        :raises ValueError: If the document cannot be identified as the
            expected game.
        """

    async def _ensure_game_validated(self) -> None:
        """
        Validate the concrete game identity once before extracting result data.

        The validation state is changed only after ``validate_game`` completes
        successfully. A failed validation therefore remains retryable and never
        marks an invalid document as trusted.

        :raises ValueError: If the loaded document does not belong to the
            concrete game.
        """
        if self._game_validated:
            return

        await self.validate_game()
        self._game_validated = True

    def _result_container(self) -> Locator:
        """
        Return the main Baloto-style result container.

        :return: Locator containing the complete draw result.
        """
        return self._page.locator("#balotoBgNew")

    def _game_id(self) -> Locator:
        """
        Return the element containing the Baloto-style draw identifier.

        :return: Locator matching the strong element that contains the draw ID.
        """
        return (
            self._result_container()
            .locator("strong")
            .filter(
                has_text=re.compile(r"\bSORTEO\b", re.IGNORECASE),
            )
        )

    def _game_date(self) -> Locator:
        """
        Return the element containing the Baloto-style draw date.

        :return: Locator matching the draw-date container.
        """
        return (
            self._result_container()
            .locator(
                "div.gotham-medium.dark-blue",
            )
            .filter(
                has_text=self._GAME_DATE_PATTERN,
            )
        )

    def _accumulated_prize(self) -> Locator:
        """
        Return the element containing the accumulated draw prize.

        :return: Locator containing the accumulated-prize text.
        """
        return self._result_container().get_by_text(
            self._ACCUMULATED_PRIZE_PATTERN,
        )

    def _winner_numbers(self) -> Locator:
        """
        Return the five regular winning-number elements.

        The locator is scoped to the result ball container and excludes the
        red superball by selecting only ``yellow-ball`` elements.

        :return: Locator containing the five regular winning numbers.
        """
        return self._result_container().locator(
            ".container-balls-results .yellow-ball",
        )

    def _balota(self) -> Locator:
        """
        Return the red superball element.

        :return: Locator containing the Baloto-style superball.
        """
        return self._result_container().locator(
            ".container-balls-results .red-ball",
        )

    def _details_container(self) -> Locator:
        """
        Return the prize-distribution section.

        :return: Locator containing the table header and category rows.
        """
        return self._result_container().locator(
            ".table-responsive",
        )

    def _details_header_row(self) -> Locator:
        """
        Return the prize-distribution header row.

        :return: Locator containing the four column headers.
        """
        return self._details_container().locator(
            "thead tr",
        )

    def _detail_rows(self) -> Locator:
        """
        Return the eight prize-category rows.

        :return: Locator containing all Baloto-style payout rows.
        """
        return self._details_container().locator(
            "tbody tr",
        )

    @staticmethod
    async def _require_exact_count(
        locator: Locator,
        expected_count: int,
        field_name: str,
    ) -> None:
        """
        Validate the exact number of currently matching DOM nodes.

        ``Locator.count`` inspects the loaded document without waiting for
        elements to appear. This permits intentionally malformed negative-test
        fixtures to fail immediately.

        :param locator: Locator whose current match count is validated.
        :param expected_count: Exact number of required nodes.
        :param field_name: Human-readable field used in validation errors.
        :raises ValueError: If the actual count differs from the expected count.
        """
        actual_count = await locator.count()

        if actual_count != expected_count:
            error_message = (
                f"Invalid Baloto-style {field_name} structure: expected {expected_count} node(s), found {actual_count}."
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
        :param field_name: Human-readable field used in validation errors.
        :return: Stripped inner text from the required node.
        :raises ValueError: If the locator does not match exactly one node.
        """
        await self._require_exact_count(
            locator,
            expected_count=1,
            field_name=field_name,
        )
        return await self.get_text(locator)

    @staticmethod
    def _normalize_hits(hits: str) -> str:
        """
        Normalize a requested prize category into its canonical representation.

        Leading, trailing, and internal whitespace is removed, and alphabetic
        characters are converted to uppercase. For example,
        ``" 2 + sb "`` becomes ``"2+SB"``.

        :param hits: Raw prize category supplied by the caller.
        :return: Normalized category suitable for Pydantic validation.
        """
        return re.sub(r"\s+", "", hits).upper()

    @classmethod
    def _validate_hits(cls, hits: str) -> BalotoHits:
        """
        Normalize and validate a Baloto-style prize category.

        :param hits: Raw category supplied by the caller or extracted from HTML.
        :return: Valid canonical prize category.
        :raises ValidationError: If the normalized category is unsupported.
        """
        normalized_hits = cls._normalize_hits(hits)
        return _BALOTO_HITS_ADAPTER.validate_python(normalized_hits)

    def _extract_table_integer(
        self,
        value: str,
        column_name: str,
    ) -> int:
        """
        Extract a Spanish-formatted integer from table-cell text.

        Currency symbols, whitespace, and surrounding content are ignored.

        :param value: Raw text extracted from a table cell.
        :param column_name: Column name included in parsing errors.
        :return: Parsed integer value.
        :raises ValueError: If the supplied text contains no valid integer.
        """
        match = self._TABLE_INTEGER_PATTERN.search(value)

        if match is None:
            error_message = f"Could not extract an integer from Baloto-style column {column_name!r}: {value!r}"
            raise ValueError(error_message)

        return parse_localized_match_to_int(match)

    async def _get_details_column_indexes(
        self,
    ) -> DetailsColumnIndexes:
        """
        Resolve the required prize-table column positions.

        Only ``ACIERTOS``, ``GANADORES``, and ``PREMIO POR GANADOR`` are
        consumed. ``PREMIO TOTAL`` remains present in the HTML but is
        intentionally ignored by the extraction contract.

        :return: Positions of the required prize-table columns.
        :raises ValueError: If the header structure is incomplete or contains
            missing required columns.
        """
        header_row = self._details_header_row()

        await self._require_exact_count(
            header_row,
            expected_count=1,
            field_name="prize-table header row",
        )

        header_cells = header_row.locator("th")

        await self._require_exact_count(
            header_cells,
            expected_count=self._DETAILS_COLUMN_COUNT,
            field_name="prize-table header columns",
        )

        headers = await header_cells.all_inner_texts()
        normalized_headers = [re.sub(r"\s+", " ", header).strip().upper() for header in headers]

        required_headers = {
            "ACIERTOS",
            "GANADORES",
            "PREMIO POR GANADOR",
        }
        missing_headers = required_headers.difference(
            normalized_headers,
        )

        if missing_headers:
            missing_columns = ", ".join(
                sorted(missing_headers),
            )
            error_message = f"The Baloto-style prize table is missing required columns: {missing_columns}."
            raise ValueError(error_message)

        return DetailsColumnIndexes(
            hits=normalized_headers.index("ACIERTOS"),
            winners=normalized_headers.index("GANADORES"),
            prize_for_winner=normalized_headers.index(
                "PREMIO POR GANADOR",
            ),
        )

    async def _get_detail_category(
        self,
        row: Locator,
        indexes: DetailsColumnIndexes,
    ) -> BalotoHits:
        """
        Extract and validate the hit category from one prize row.

        :param row: Locator representing one prize-category row.
        :param indexes: Resolved table-column positions.
        :return: Canonical Baloto-style prize category.
        :raises ValueError: If the row does not contain the expected cells.
        :raises ValidationError: If the extracted category is unsupported.
        """
        cells = row.locator("td")

        await self._require_exact_count(
            cells,
            expected_count=self._DETAILS_COLUMN_COUNT,
            field_name="prize-table row cells",
        )

        category_text = await self.get_text(
            cells.nth(indexes.hits),
        )
        normalized_category = normalize_baloto_hits_key(
            category_text,
        )

        return self._validate_hits(normalized_category)

    async def _parse_detail_row(
        self,
        row: Locator,
        indexes: DetailsColumnIndexes,
    ) -> tuple[BalotoHits, ResultDetailsSchema] | None:
        """
        Convert one prize-table row into payout information.

        Rows reporting zero winners are structurally validated but return
        ``None`` because no payout record should be persisted for them.

        :param row: Locator representing one prize-category row.
        :param indexes: Resolved table-column positions.
        :return: Category and payout details, or ``None`` for zero winners.
        :raises ValueError: If required cells are missing or numeric values are
            invalid.
        :raises ValidationError: If the extracted category is unsupported.
        """
        cells = row.locator("td")

        await self._require_exact_count(
            cells,
            expected_count=self._DETAILS_COLUMN_COUNT,
            field_name="prize-table row cells",
        )

        category = await self._get_detail_category(
            row,
            indexes,
        )

        winners_text = await self.get_text(
            cells.nth(indexes.winners),
        )
        winners = self._extract_table_integer(
            winners_text,
            "GANADORES",
        )

        if winners == 0:
            return None

        prize_text = await self.get_text(
            cells.nth(indexes.prize_for_winner),
        )
        prize_for_winner = self._extract_table_integer(
            prize_text,
            "PREMIO POR GANADOR",
        )

        return category, ResultDetailsSchema(
            prize_for_winner=prize_for_winner,
            winners=winners,
        )

    async def _get_validated_detail_rows(self) -> list[Locator]:
        """
        Return the complete validated prize-row collection.

        :return: Eight prize-category row locators.
        :raises ValueError: If the document does not contain exactly eight
            prize-category rows.
        """
        rows_locator = self._detail_rows()

        await self._require_exact_count(
            rows_locator,
            expected_count=self._DETAILS_COUNT,
            field_name="prize-category rows",
        )

        return await rows_locator.all()

    async def validate_draw_id(self) -> None:
        """
        Verify that the loaded HTML belongs to the expected draw.

        Game identity is validated automatically before comparing the draw
        identifiers.

        :raises ValueError: If the game identity is invalid or the displayed
            and expected draw identifiers differ.
        """
        await self._ensure_game_validated()

        actual_draw_id = await self.get_game_id()
        validate_draw_id(
            self._draw_id,
            actual_draw_id,
        )

    async def get_draw_title(self) -> str:
        """
        Return the normalized draw title displayed in the result document.

        :return: Draw title such as ``SORTEO 2.686``.
        :raises ValueError: If the game identity is invalid or the title node
            is missing or duplicated.
        """
        await self._ensure_game_validated()

        return await self._get_required_text(
            self._game_id(),
            "draw identifier",
        )

    async def get_game_id(self) -> int:
        """
        Extract and normalize the loaded draw identifier.

        A displayed value such as ``SORTEO 2.686`` is returned as ``2686``.

        :return: Parsed draw identifier.
        :raises ValueError: If the game identity is invalid or the identifier
            cannot be extracted.
        """
        await self._ensure_game_validated()

        text = await self._get_required_text(
            self._game_id(),
            "draw identifier",
        )
        match = self._GAME_ID_PATTERN.fullmatch(text)

        if match is None:
            error_message = f"Could not extract the {self.game_name} draw identifier from: {text!r}"
            raise ValueError(error_message)

        return parse_localized_match_to_int(match)

    async def get_game_date(self) -> str:
        """
        Return the draw date exactly as displayed by the website.

        Date parsing and conversion into ``datetime.date`` remain the
        responsibility of the consuming schema or service.

        :return: Spanish date text such as ``22 de Julio de 2026``.
        :raises ValueError: If the game identity is invalid or the date node is
            missing or duplicated.
        """
        await self._ensure_game_validated()

        return await self._get_required_text(
            self._game_date(),
            "draw date",
        )

    async def get_accumulated_prize(self) -> int:
        """
        Extract the accumulated prize and normalize it to Colombian pesos.

        A displayed value such as ``$49.200 MILLONES`` is converted into
        ``49_200_000_000``.

        :return: Accumulated prize expressed in Colombian pesos.
        :raises ValueError: If the game identity is invalid or the accumulated
            value cannot be extracted.
        """
        await self._ensure_game_validated()

        text = await self._get_required_text(
            self._accumulated_prize(),
            "accumulated prize",
        )
        match = self._ACCUMULATED_PRIZE_PATTERN.fullmatch(
            text,
        )

        if match is None:
            error_message = f"Could not extract the {self.game_name} accumulated prize from: {text!r}"
            raise ValueError(error_message)

        return parse_millions_to_pesos(
            match.group(1),
        )

    async def get_winner_numbers(self) -> list[int]:
        """
        Extract the five regular winning numbers.

        The red superball is excluded. Values such as ``"03"`` are normalized
        to integers such as ``3``.

        :return: Five regular winning numbers in displayed order.
        :raises ValueError: If the game identity is invalid, the number of nodes
            is incorrect, or a value cannot be converted to an integer.
        """
        await self._ensure_game_validated()

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
            error_message = f"Invalid {self.game_name} winning-number values: {number_texts!r}"
            raise ValueError(error_message) from error

    async def get_balota(self) -> int:
        """
        Extract the red superball number.

        :return: Parsed red superball number.
        :raises ValueError: If the game identity is invalid or the superball
            cannot be extracted.
        """
        await self._ensure_game_validated()

        balota_text = await self._get_required_text(
            self._balota(),
            "superball",
        )

        try:
            return int(balota_text)
        except ValueError as error:
            error_message = f"Invalid {self.game_name} superball value: {balota_text!r}"
            raise ValueError(error_message) from error

    async def get_detail(
        self,
        hits: str,
    ) -> ResultDetailsSchema | None:
        """
        Return payout information for one requested prize category.

        The input is normalized before validation. Values such as ``"2+SB"``,
        ``"2+sb"``, and ``" 2 + sb "`` therefore represent the same canonical
        category.

        The result document must contain all eight expected prize rows.
        ``None`` is returned only when the requested category exists and reports
        zero winners.

        :param hits: Baloto-style prize category to retrieve.
        :return: Payout information, or ``None`` when the category has no
            registered winners.
        :raises ValidationError: If ``hits`` is not a supported category.
        :raises ValueError: If the game identity is invalid, the requested
            category is missing, or its row is structurally invalid.
        """
        await self._ensure_game_validated()

        validated_hits = self._validate_hits(hits)
        rows = await self._get_validated_detail_rows()
        indexes = await self._get_details_column_indexes()

        for row in rows:
            category = await self._get_detail_category(
                row,
                indexes,
            )

            if category != validated_hits:
                continue

            parsed_detail = await self._parse_detail_row(
                row,
                indexes,
            )

            if parsed_detail is None:
                return None

            return parsed_detail[1]

        error_message = (
            f"The {self.game_name} result document does not contain the expected hit category {validated_hits!r}."
        )
        raise ValueError(error_message)

    async def get_details(self) -> dict[str, ResultDetailsSchema]:
        """
        Extract payout details for all categories with registered winners.

        All eight expected categories are structurally validated. Categories
        whose winner count is zero are omitted from the returned dictionary so
        empty payout rows are not propagated toward persistence.

        :return: Mapping of awarded categories to payout information.
        :raises ValidationError: If an extracted category is unsupported.
        :raises ValueError: If the game identity is invalid or categories are
            missing, duplicated, or malformed.
        """
        await self._ensure_game_validated()

        rows = await self._get_validated_detail_rows()
        indexes = await self._get_details_column_indexes()
        details: dict[str, ResultDetailsSchema] = {}
        discovered_categories: set[BalotoHits] = set()

        for row in rows:
            category = await self._get_detail_category(
                row,
                indexes,
            )

            if category in discovered_categories:
                error_message = f"Duplicate {self.game_name} hit category found in the result document: {category!r}."
                raise ValueError(error_message)

            discovered_categories.add(category)

            parsed_detail = await self._parse_detail_row(
                row,
                indexes,
            )

            if parsed_detail is None:
                continue

            parsed_category, result_schema = parsed_detail
            details[parsed_category] = result_schema

        if discovered_categories != self._EXPECTED_HITS:
            missing_categories = sorted(
                self._EXPECTED_HITS.difference(
                    discovered_categories,
                ),
            )
            error_message = (
                f"The {self.game_name} result document is missing expected hit categories: {missing_categories!r}."
            )
            raise ValueError(error_message)

        return details


class BalotoPage(_BalotoResultPage):
    """Extract and automatically validate Baloto draw results."""

    @property
    def result_url(self) -> HttpUrl:
        """
        Return the configured Baloto results URL.

        :return: Configured Baloto results URL.
        """
        return settings.baloto_settings.baloto_baseurl

    @property
    def game_name(self) -> str:
        """
        Return the Baloto game name.

        :return: ``"Baloto"``.
        """
        return "Baloto"

    async def validate_game(self) -> None:
        """
        Verify that the loaded result document belongs to Baloto.

        Production HTML is identified through the Baloto result image. Clean
        static fixtures are identified through ``body[data-game="baloto"]``.

        This method inspects the DOM directly and must not invoke any public
        extraction operation.

        :raises ValueError: If neither Baloto identifier exists.
        """
        game_markers = self._page.locator(
            'body[data-game="baloto"], img[src$="baloto.png"]',
        )
        marker_count = await game_markers.count()

        if marker_count == 0:
            error_message = "The loaded result document does not belong to Baloto."
            raise ValueError(error_message)


class RevanchaPage(_BalotoResultPage):
    """Extract and automatically validate Revancha draw results."""

    @property
    def result_url(self) -> HttpUrl:
        """
        Return the configured Revancha results URL.

        :return: Configured Revancha results URL.
        """
        return settings.baloto_settings.revancha_baseurl

    @property
    def game_name(self) -> str:
        """
        Return the Revancha game name.

        :return: ``"Revancha"``.
        """
        return "Revancha"

    async def validate_game(self) -> None:
        """
        Verify that the loaded result document belongs to Revancha.

        Production HTML is identified through the Revancha result image. Clean
        static fixtures are identified through ``body[data-game="revancha"]``.

        This method inspects the DOM directly and must not invoke any public
        extraction operation.

        :raises ValueError: If neither Revancha identifier exists.
        """
        game_markers = self._page.locator(
            'body[data-game="revancha"], img[src$="revancha.png"]',
        )
        marker_count = await game_markers.count()

        if marker_count == 0:
            error_message = "The loaded result document does not belong to Revancha."
            raise ValueError(error_message)

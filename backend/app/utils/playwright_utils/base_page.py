"""
Provide the asynchronous base page object and shared lottery utilities.

This module defines the common foundation used by page objects implemented
with Playwright's asynchronous Python API.

The ``BasePage`` class is responsible for:

- Storing the active Playwright ``Page`` instance.
- Building absolute URLs from a base URL and a page-specific path.
- Providing shared navigation operations.
- Reading normalized element text.
- Providing reusable web-first assertions.

The module also provides data structures and parsing utilities shared by
Baloto, Revancha, and MiLoto result pages.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from re import Match
from typing import TYPE_CHECKING

from babel.numbers import NumberFormatError, parse_number
from playwright.async_api import Locator, Page, expect

if TYPE_CHECKING:
    from pydantic import HttpUrl


@dataclass(frozen=True, slots=True)
class DetailsColumnIndexes:
    """
    Store required column positions from a prize-details table.

    The indexes identify the columns used to extract the prize category,
    number of winners, and prize awarded to each winner.

    :param hits: Position of the ``ACIERTOS`` column.
    :param winners: Position of the ``GANADORES`` column.
    :param prize_for_winner: Position of the ``PREMIO POR GANADOR`` column.
    """

    hits: int
    winners: int
    prize_for_winner: int

    @property
    def maximum(self) -> int:
        """
        Return the highest required column index.

        :return: Highest configured column index.
        """
        return max(self.hits, self.winners, self.prize_for_winner)


class BasePage(ABC):
    """
    Provide shared asynchronous behavior for application page objects.

    Subclasses must implement the ``path`` property. Page-specific locators,
    extraction rules, and workflows should remain in concrete page classes.
    """

    def __init__(self, page: Page) -> None:
        """
        Initialize the base page object.

        :param page: Active Playwright page controlled by the current test.
        :param base_url: Root URL of the application under test.
        :raises ValueError: If ``base_url`` is empty or contains only whitespace.
        """
        self._page = page

    @property
    @abstractmethod
    def result_url(self) -> HttpUrl:
        """
        Return the public URL of the configured lottery draw.

        The URL is metadata used by the HTML-loading service. ``BasePage``
        itself does not navigate to this URL.

        :return: Fully qualified URL for the configured draw.
        """

    @property
    @abstractmethod
    def game_name(self) -> str:
        """
        Return the canonical name of the lottery game.

        :return: Stable game name used for validation and reporting.
        """

    async def get_text(
        self,
        locator: Locator,
        *,
        timeout_ms: float = 30_000,
    ) -> str:
        """
        Return normalized inner text from an element.

        :param locator: Element whose text should be retrieved.
        :param timeout_ms: Maximum waiting time in milliseconds.
        :return: Element text without leading or trailing whitespace.
        """
        return (await locator.inner_text(timeout=timeout_ms)).strip()

    async def expect_visible(
        self,
        locator: Locator,
        *,
        timeout_ms: float = 5_000,
    ) -> None:
        """
        Assert that an element becomes visible.

        :param locator: Element expected to become visible.
        :param timeout_ms: Maximum assertion time in milliseconds.
        """
        await expect(locator).to_be_visible(timeout=timeout_ms)


def parse_millions_to_pesos(localized_millions: str) -> int:
    """
    Convert a Spanish-formatted amount in millions into pesos.

    A value such as ``"46.400"`` is parsed using the Spanish locale as
    ``46_400`` and multiplied by one million.

    :param localized_millions: Numeric amount expressed in millions.
    :return: Complete amount expressed in pesos.
    :raises ValueError: If the supplied value cannot be parsed.
    """
    normalized_value = localized_millions.strip()

    try:
        millions = parse_number(normalized_value, locale="es")
    except NumberFormatError as error:
        error_message = f"Invalid localized millions value: {localized_millions!r}"
        raise ValueError(error_message) from error

    return int(millions) * 1_000_000


def parse_localized_match_to_int(
    match: Match[str],
    *,
    group: int | str = 1,
) -> int:
    """
    Parse a regex group containing a Spanish-formatted integer.

    A captured value such as ``"2.679"`` is interpreted as ``2679`` using
    Babel with the Spanish locale.

    :param match: Successful regular-expression match containing the number.
    :param group: Numeric or named capture group containing the localized value.
    :return: Parsed integer value.
    :raises ValueError: If the selected group is missing, empty, or invalid.
    """
    try:
        localized_value = match.group(group)
    except IndexError as error:
        error_message = f"Regex group {group!r} does not exist."
        raise ValueError(error_message) from error

    if localized_value is None or not localized_value.strip():
        error_message = f"Regex group {group!r} does not contain a value."
        raise ValueError(error_message)

    try:
        return int(parse_number(localized_value.strip(), locale="es"))
    except NumberFormatError as error:
        error_message = f"Invalid Spanish-formatted integer: {localized_value!r}"
        raise ValueError(error_message) from error


def normalize_baloto_hits_key(hits_text: str) -> str:
    """
    Normalize a Baloto or Revancha prize category.

    The displayed category ``0 + SB`` represents matching only the superball
    and is normalized to ``SB``.

    Supported keys are ``SB``, ``2+SB``, ``3``, ``3+SB``, ``4``, ``4+SB``,
    ``5``, and ``5+SB``.

    :param hits_text: Category text extracted from the ``ACIERTOS`` column.
    :return: Normalized prize-category key.
    :raises ValueError: If the category is not supported.
    """
    normalized_hits = re.sub(r"\s+", "", hits_text).upper()

    category_mapping = {
        "0+SB": "SB",
        "SB": "SB",
        "2+SB": "2+SB",
        "3": "3",
        "3+SB": "3+SB",
        "4": "4",
        "4+SB": "4+SB",
        "5": "5",
        "5+SB": "5+SB",
    }

    category = category_mapping.get(normalized_hits)

    if category is None:
        error_message = f"Unsupported prize category: {hits_text!r}"
        raise ValueError(error_message)

    return category


def validate_draw_id(expected_draw_id: int, actual_draw_id: int) -> None:
    """
    Verify that the loaded result belongs to the requested lottery draw.

    The function compares the identifier requested by the caller with the
    identifier extracted from the loaded HTML. A mismatch indicates that the
    wrong document was loaded or that the website returned unexpected content.

    :param expected_draw_id: Draw identifier requested by the caller.
    :param actual_draw_id: Draw identifier extracted from the loaded document.
    :raises ValueError: If both identifiers do not match.
    """
    if actual_draw_id != expected_draw_id:
        error_message = f"Loaded draw ID {actual_draw_id} does not match the expected draw ID {expected_draw_id}."
        raise ValueError(error_message)

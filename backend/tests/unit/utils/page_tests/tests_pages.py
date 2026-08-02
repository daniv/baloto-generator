"""Test the shared contract implemented by lottery result pages."""

from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.utils.playwright_utils import BalotoPage, ResultPage, RevanchaPage
    from playwright.async_api import Page

    from tests.unit.utils.page_tests.models import ValidGames


@pytest.mark.crossgames
@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("expected_key", ["no_jackpot", "jackpot"])
async def test_validate_all_fields(
    game_name: ValidGames,
    expected_result: dict[str, Any],
    case_page: Page,
    result_page_factory: Callable[[Page, int], ResultPage],
    expected_key: str,
) -> None:
    """
    Validate the complete extraction behavior for every lottery result page.

    The test loads the mocked HTML associated with each game and scenario,
    creates the corresponding result-page object, and verifies every expected
    field extracted from the document.

    :param game_name: Lottery game selected for the parametrized execution.
    :param expected_result: Mutable copy of the expected scenario values.
    :param case_page: Playwright page loaded with the scenario HTML.
    :param result_page_factory: Factory for the selected result-page type.
    :param expected_key: Expected-result scenario identifier.
    :return: None.
    """
    expected = expected_result

    required_fields = {
        "game_id",
        "game_date",
        "winner_numbers",
        "accumulated_prize",
        "details",
    }
    if game_name != "miloto":
        required_fields.add("balota")

    missing_fields = required_fields.difference(expected)

    assert not missing_fields, (
        f"Missing expected fields for game={game_name!r}, "
        f"case={expected_key!r}: {sorted(missing_fields)}. "
        f"Available fields: {sorted(expected)}"
    )

    game_id = expected.pop("game_id")
    expected_game_date = expected.pop("game_date")
    expected_winner_numbers = expected.pop("winner_numbers")
    expected_accumulated_prize = expected.pop("accumulated_prize")
    expected_details = expected.pop("details")

    result_page = result_page_factory(case_page, game_id)

    game_display_name = game_name.capitalize()
    hits = ("SB", "2+SB", "3", "3+SB", "4", "5", "5+SB")
    if game_name == "miloto":
        hits = ("2", "3", "4", "5")

    if game_name != "miloto":
        expected_balota = expected.pop("balota")
        br_page = cast("BalotoPage", result_page) if game_name == "baloto" else cast("RevanchaPage", result_page)
        actual_balota = await br_page.get_balota()

        assert actual_balota == expected_balota, (
            f"Unexpected balota for game={game_name!r}, "
            f"case={expected_key!r}. "
            f"Expected: {expected_balota!r}. "
            f"Actual: {actual_balota!r}."
        )

    actual_game_id = await result_page.get_game_id()
    assert actual_game_id == game_id, (
        f"Unexpected game identifier for game={game_name!r}, "
        f"case={expected_key!r}. "
        f"Expected: {game_id!r}. "
        f"Actual: {actual_game_id!r}."
    )

    actual_game_date = await result_page.get_game_date()
    assert actual_game_date == expected_game_date, (
        f"Unexpected game date for game={game_name!r}, "
        f"case={expected_key!r}. "
        f"Expected: {expected_game_date!r}. "
        f"Actual: {actual_game_date!r}."
    )

    actual_winner_numbers = await result_page.get_winner_numbers()
    assert actual_winner_numbers == expected_winner_numbers, (
        f"Unexpected winner numbers for game={game_name!r}, "
        f"case={expected_key!r}. "
        f"Expected: {expected_winner_numbers!r}. "
        f"Actual: {actual_winner_numbers!r}."
    )

    actual_accumulated_prize = await result_page.get_accumulated_prize()
    assert actual_accumulated_prize == expected_accumulated_prize, (
        f"Unexpected accumulated prize for game={game_name!r}, "
        f"case={expected_key!r}. "
        f"Expected: {expected_accumulated_prize!r}. "
        f"Actual: {actual_accumulated_prize!r}."
    )

    actual_details = await result_page.get_details()

    for hit in hits:
        detail_key = f"hits_{hit.lower().replace('+', '_')}"
        actual_detail = actual_details.get(hit)

        if detail_key not in expected_details:
            assert actual_detail is None, (
                f"Unexpected payout category for game={game_name!r}, "
                f"case={expected_key!r}, category={hit!r}. "
                f"Actual: {actual_detail!r}."
            )
            continue

        expected_detail = expected_details[detail_key]

        assert actual_detail is not None, (
            f"Missing payout category for game={game_name!r}, "
            f"case={expected_key!r}, category={hit!r}. "
            f"Expected: {expected_detail!r}."
        )

        assert actual_detail.winners == expected_detail["winners"], (
            f"Unexpected winner count for {game_display_name} "
            f"case={expected_key!r}, category={hit!r}. "
            f"Expected: {expected_detail['winners']!r}. "
            f"Actual: {actual_detail.winners!r}."
        )

        assert actual_detail.prize_for_winner == expected_detail["prize_for_winner"], (
            f"Unexpected prize per winner for {game_display_name} "
            f"case={expected_key!r}, category={hit!r}. "
            f"Expected: {expected_detail['prize_for_winner']!r}. "
            f"Actual: {actual_detail.prize_for_winner!r}."
        )

    assert not expected, (
        f"Expected fields were not validated for game={game_name!r}, case={expected_key!r}: {sorted(expected)}."
    )

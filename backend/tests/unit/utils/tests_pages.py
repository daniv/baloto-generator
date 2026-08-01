"""Test the shared contract implemented by lottery result pages."""

from typing import TYPE_CHECKING, Any, cast

import anyio
import pytest
from app.utils.playwright_utils import BalotoPage, MilotoPage, RevanchaPage
from playwright.async_api import async_playwright

from tests.constants import MOCKED_HTML_RESOURCES_DIRECTORY

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable
    from pathlib import Path

    from app.utils.playwright_utils import ResultPage


@pytest.fixture
async def result_page_fix() -> AsyncGenerator[Callable[[str, str, int, Path], Awaitable[ResultPage]]]:
    """
    Provide a factory that creates result-page objects from local HTML fixtures.

    Playwright, the browser, the browser context, and the page remain active
    during the complete test. The fixture closes every resource deterministically
    after the test finishes.

    The same browser page is reused when the factory is invoked more than once
    during one test. Each invocation replaces its current document through
    ``Page.set_content``.

    :yield: Asynchronous factory that receives the game type, result key, and
        local HTML path and returns the corresponding result-page object.
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(locale="es-CO")
        browser_page = await context.new_page()

        async def _result_page_factory(
            gtype: str,
            key: str,
            draw_id: int,
            mocked_html_path: Path,
        ) -> ResultPage:
            """
            Load one local result document and create its page object.

            :param gtype: Supported game name.
            :param key: Result identifier beginning with the numeric draw ID.
            :param draw_id: The numeric draw ID.
            :param mocked_html_path: Path to the local HTML fixture.
            :return: Page object associated with the requested game.
            :raises ValueError: If ``gtype`` is unsupported.
            """
            html_content = await anyio.Path(mocked_html_path).read_text(encoding="utf-8")

            await browser_page.set_content(html_content)

            match gtype:
                case "miloto":
                    return MilotoPage(browser_page, draw_id)
                case "baloto":
                    return BalotoPage(browser_page, draw_id)
                case "revancha":
                    return RevanchaPage(browser_page, draw_id)
                case _:
                    error_message = f"Unsupported game name: {gtype}"
                    raise ValueError(error_message)

        try:
            yield _result_page_factory
        finally:
            await context.close()
            await browser.close()


# uv --directory backend run pytest tests/unit/utils/tests_pages.py --pdb -x -vv
#
# n — ejecuta la siguiente línea sin entrar en funciones.
# s — entra en la función llamada en la línea actual.
# c — continúa hasta el próximo breakpoint o hasta terminar.
# r — continúa hasta que termine la función actual.
# l — muestra el código alrededor de la línea actual.
# ll — muestra toda la función actual.
# p variable — imprime una variable.
# pp variable — imprime una variable con formato más legible.
# args — muestra los argumentos de la función actual.
# w — muestra el stack trace.
# u — sube un nivel en el stack.
# d — baja un nivel en el stack.
# b 120 — crea un breakpoint en la línea 120.
# b archivo.py:120 — crea un breakpoint en un archivo y línea.
# cl — lista o elimina breakpoints.
# q — termina la sesión de depuración.
# h — muestra ayuda.


@pytest.mark.parametrize("game_type", ["miloto", "baloto", "revancha"])
@pytest.mark.parametrize("result_key", ["no_jackpot", "jackpot"])
async def test_validate_all_fields(
    testpages_stash: dict[str, Any],
    result_page_fix: Callable[[str, str, int, Path], Awaitable[ResultPage]],
    game_type: str,
    result_key: str,
) -> None:
    """
    Validate the complete extraction behavior for every lottery page object.

    The test loads the matching mocked HTML fixture for each supported game and
    verifies that the page object extracts every expected result field correctly,
    including the game identifier, draw date, winning numbers, accumulated prize,
    balota when applicable, and payout details.
    """
    if "skip" in testpages_stash:
        reason_msg = testpages_stash.pop("skip", "")
        pytest.skip(reason=reason_msg)
        return

    hits = ("SB", "2+SB", "3", "3+SB", "4", "5", "SB")
    brm = game_type.capitalize()
    if game_type == "miloto":
        hits = ("2", "3", "4", "5")

    mocked_html_path = MOCKED_HTML_RESOURCES_DIRECTORY / testpages_stash.pop("html_file", "")
    expected = testpages_stash.pop("expected", {})
    draw_id = expected.get("game_id", 0)
    result_page: ResultPage = await result_page_fix(game_type, result_key, draw_id, mocked_html_path)

    expected_game_id = expected.pop("game_id", "")
    expected_game_date = expected.pop("game_date", "")
    expected_winner_numbers = expected.pop("winner_numbers", [])
    expected_accumulated_prize = expected.pop("accumulated_prize", 0)
    expected_details = expected.pop("details", {})
    if game_type != "miloto":
        expected_balota = expected.pop("balota", 0)
        br_page = cast("BalotoPage", result_page) if game_type == "baloto" else cast("RevanchaPage", result_page)
        assert await br_page.get_balota() == expected_balota, f"Unexpected 'get_balota()' value found for {game_type}"

    assert await result_page.get_game_id() == expected_game_id, (
        f"Unexpected 'get_game_id()' value found for {game_type}"
    )

    assert await result_page.get_game_date() == expected_game_date, (
        f"Unexpected 'get_game_date()' value found for {game_type}"
    )

    assert await result_page.get_winner_numbers() == expected_winner_numbers, (
        f"Unexpected 'get_winner_numbers()' value found for {game_type}"
    )

    assert await result_page.get_accumulated_prize() == expected_accumulated_prize, (
        f"Unexpected 'get_accumulated_prize()' value found for {game_type}"
    )
    for hit in hits:
        expected_key = f"hits_{hit.lower().replace('+', '_')}"
        actual_detail = await result_page.get_detail(hit)

        if expected_key not in expected_details:
            assert actual_detail is None, f"Unexpected payout for {brm} category {hit!r}."
            continue

        expected_detail = expected_details[expected_key]

        assert actual_detail is not None, f"Missing payout for {brm} category {hit!r}."
        assert actual_detail.winners == expected_detail["winners"], f"Invalid winner count for {brm} category {hit!r}."
        assert actual_detail.prize_for_winner == expected_detail["prize_for_winner"], (
            f"Invalid prize per winner for {brm} category {hit!r}."
        )

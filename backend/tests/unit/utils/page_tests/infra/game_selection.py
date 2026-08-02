"""Test game selection performed by the page-test pytest hooks."""

import os
from pathlib import Path
from textwrap import dedent

import pytest

pytest_plugins = ("pytester",)


@pytest.mark.parametrize(
    (
        "marker_expression",
        "cli_arguments",
        "expected_games",
        "expected_passed",
    ),
    [
        pytest.param(
            'only_game("baloto")',
            (),
            ("baloto",),
            1,
            id="only-baloto",
        ),
        pytest.param(
            'skip_game("miloto")',
            (),
            ("baloto", "revancha"),
            2,
            id="skip-miloto",
        ),
        pytest.param(
            "crossgames",
            (),
            ("miloto", "baloto", "revancha"),
            3,
            id="crossgames",
        ),
        pytest.param(
            "crossgames",
            ("--game", "baloto"),
            ("baloto",),
            1,
            id="cli-filter",
        ),
    ],
)
def test_game_marker_generates_expected_cases(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    marker_expression: str,
    cli_arguments: tuple[str, ...],
    expected_games: tuple[str, ...],
    expected_passed: int,
) -> None:
    """
    Verify that game markers generate only their applicable test cases.

    :param pytester: Temporary pytest environment.
    :param monkeypatch: Environment modifier for the isolated subprocess.
    :param marker_expression: Marker expression applied to the temporary test.
    :param cli_arguments: Additional pytest command-line arguments.
    :param expected_games: Games expected to reach the temporary test.
    :param expected_passed: Number of generated passing test cases.
    :return: None.
    """
    backend_root = Path(__file__).resolve().parents[5]
    current_pythonpath = os.environ.get("PYTHONPATH", "")

    subprocess_pythonpath = os.pathsep.join(value for value in (str(backend_root), current_pythonpath) if value)

    monkeypatch.setenv("PYTHONPATH", subprocess_pythonpath)

    pytester.makeconftest(
        dedent(
            """
            from tests.conftest import pytest_addoption
            from tests.unit.utils.conftest import pytest_configure
            from tests.unit.utils.page_tests.conftest import pytest_generate_tests
            """
        )
    )

    pytester.makepyfile(
        test_selection=dedent(
            f"""
            import pytest


            @pytest.mark.{marker_expression}
            def test_selected_game(game_name):
                assert game_name in {expected_games!r}
            """
        )
    )

    result = pytester.runpytest_subprocess("-q", *cli_arguments)
    result.assert_outcomes(passed=expected_passed)

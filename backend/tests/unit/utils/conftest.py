"""
Configure collection-time resources for lottery page-object tests.

This module connects parametrized page tests with their external expected-result
JSON files. It performs the following responsibilities:

- Inspect each ``tests_pages`` parametrized case during pytest setup.
- Resolve the expected-results JSON file for the selected lottery game.
- Store skip reasons and resource metadata in ``pytest.Stash``.
- Skip test cases whose required expected-results file is unavailable.
- Load the expected result data consumed by the page-object test fixtures.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from tests.constants import MOCKED_HTML_RESOURCES_DIRECTORY, XPECTED_RESULTS_RESOURCES_DIRECTORY

if TYPE_CHECKING:
    from _pytest.python import CallSpec2


TESTPAGES_STASH = pytest.StashKey[dict[str, Any]]()

# region Pytest hooks


@pytest.hookimpl
def pytest_runtest_setup(item: pytest.Item) -> None:
    """
    Prepare external expected-result resources for parametrized page tests.

    The hook inspects ``tests_pages`` cases, resolves the JSON file associated
    with the selected lottery game, and stores either the resource metadata or
    a skip reason in ``pytest.Stash``.

    :param item: Pytest test item being prepared for execution.
    """
    module_name = Path(item.location[0]).stem
    if module_name != "tests_pages":
        return
    if not hasattr(item, "callspec"):
        return
    callspec: CallSpec2 | None = getattr(item, "callspec", None)
    if callspec is None:
        return

    callspec_game = str(callspec.params["game_type"])
    callspec_key = str(callspec.params["result_key"])
    callspec_id = callspec.id

    # building the path for the miloto.json file
    xpected_json: Path = XPECTED_RESULTS_RESOURCES_DIRECTORY / module_name / f"{callspec_game}.json"
    if not xpected_json.exists():
        skip_reason = (
            f"The {callspec_game}.json expected results file was not found on "
            f"{xpected_json!s} for testid: {callspec_id}"
        )
        item.stash[TESTPAGES_STASH] = {"skip": skip_reason}
        return

    xpected_data = _get_expected_results(item, xpected_json, callspec_key, callspec_id)
    if xpected_data is None:
        return

    file_to_test = xpected_data["html_file"]
    mocked_path_str = _validate_mocked_html_exists(item, file_to_test, callspec_id)
    if mocked_path_str is None:
        return
    item.stash[TESTPAGES_STASH] = xpected_data


# endregion


# region Module scoped fixtures


@pytest.fixture
def testpages_stash(request: pytest.FixtureRequest) -> dict[str, Any]:
    """
    Return expected data stored for the active test item.

    :param request: Fixture request associated with the active test.
    :return: Expected data stored during ``pytest_runtest_setup``.
    :raises LookupError: If the active node does not contain expected data.
    """
    node = getattr(request, "node", None)
    if node is None:
        error_message = "No active test node found in the fixture request."
        raise LookupError(error_message)
    stash = getattr(node, "stash", None)
    if stash is None:
        error_message = f"No stash attribute found on the active test node: {node!r}."
        raise LookupError(error_message)

    if TESTPAGES_STASH not in node.stash:
        error_message = f"No expected data found for {node.nodeid}. Node type: {type(node).__name__}."
        raise LookupError(error_message)

    return stash[TESTPAGES_STASH]


# endregion


# region Local service functions


def _get_expected_results(item: pytest.Item, json_path: Path, key: str, tid: str) -> dict[str, Any] | None:
    with json_path.open(encoding="utf-8") as file:
        data = json.load(file)

    if key not in data:
        skip_reason = f"The expected tag '{key}' was not found on miloto.json for testid: {tid}"
        item.stash[TESTPAGES_STASH] = {"skip": skip_reason}
        return None

    return data[key]


def _validate_mocked_html_exists(item: pytest.Item, file_to_test: str, tid: str) -> str | None:
    file_path: Path = MOCKED_HTML_RESOURCES_DIRECTORY / file_to_test
    if not file_path.exists():
        skip_reason = f"The result file '{file_to_test}' was not found on {file_path!s} for testid: {tid}"
        item.stash[TESTPAGES_STASH] = {"skip": skip_reason}
        return None
    return str(file_path)


# endregion

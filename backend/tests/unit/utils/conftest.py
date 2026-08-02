"""Configure pytest markers and game parametrization for utility unit tests."""

import pytest

GAMES_LIST: tuple[str, ...] = ("miloto", "baloto", "revancha")

# region Pytest hooks


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """
    Register the custom pytest markers used by page-object tests.

    :param config: Active pytest configuration object.
    :return: None.
    """
    config.addinivalue_line("markers", "skip_game(name): mark test to be skipped a specific game")
    config.addinivalue_line("markers", "only_game(name): mark test to run only on a specific game")
    config.addinivalue_line("markers", "crossgames: runs the test on all games engines (miloto, baloto and revancha)")


# endregion

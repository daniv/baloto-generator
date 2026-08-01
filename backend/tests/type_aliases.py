"""Define reusable callable contracts and type aliases for the test suite."""

from collections.abc import Callable, Coroutine
from typing import Any, Protocol

from app.utils.playwright_utils import ResultPage
from playwright.async_api import Page


class RunAsync(Protocol):
    """Define a callable that executes coroutines on the test event loop."""

    def __call__[T](self, coroutine: Coroutine[Any, Any, T]) -> T:
        """
        Execute a coroutine and return its result.

        :param coroutine: Coroutine to execute.
        :return: Value produced by the coroutine.
        """
        ...


type ResultPageFactory = Callable[[Page, int], ResultPage]

__all__ = ["ResultPageFactory", "RunAsync"]

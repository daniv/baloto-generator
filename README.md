## Backend quality checks

Run commands from the `backend` directory.

- `uv run poe check` — run formatting, linting, type checking, and tests.
- `uv run poe check-all` — run all checks, including deferred documentation rules.
- `uv run poe format` — format backend source and tests.
- `uv run poe lint-fix` — apply safe Ruff fixes.
- `uv run poe test` — run the backend test suite.
- `uv run poe typecheck` — run Pyright in strict mode.

Current known items:

- Public module, class, and method docstrings are deferred.
- Starlette currently emits a deprecation warning related to `httpx` and `httpx2`.
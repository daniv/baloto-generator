## Backend quality checks

Run backend Poe tasks from the repository root:

```bash
uv --directory backend run poe check-all
```

## statistics

```bash
uv run ruff check app tests --statistics
```

## fix

```bash
uv run ruff check app tests --select I001,W293 --fix
```
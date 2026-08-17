# Contributing

This repository is an empirical research project. Contributions should preserve the accounting identities, source traceability and reproducibility guarantees documented in `README.md`, `METHODOLOGY.md` and `DATA_DICTIONARY.md`.

## Development Setup

Use Poetry:

```bash
poetry install
```

Or use any Python 3.11+ environment with the dependencies declared in `pyproject.toml`.

## Validation

Before opening a pull request, run:

```bash
make test
```

For a full rebuild, run:

```bash
make all
```

If the change touches style, typing or shared Python code, also run:

```bash
poetry run ruff check .
poetry run mypy src
```

## Data Changes

- Do not overwrite files in `data/raw/` unless the source file itself has intentionally changed.
- Keep raw-file hashes current in `outputs/metrics/raw_file_sha256.json`.
- Persist derived tables to CSV so results can be inspected without notebook state.
- Document source coverage gaps and methodological caveats explicitly.

## Pull Requests

Pull requests should include:

- what changed;
- why the change is needed;
- which sources or outputs are affected;
- which validation commands were run.

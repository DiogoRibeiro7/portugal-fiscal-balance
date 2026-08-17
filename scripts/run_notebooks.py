#!/usr/bin/env python
"""Execute the notebooks in lexical order and persist their outputs in place.

Outputs are committed with the notebooks so the narrative is readable on GitHub
without running anything. Two things are done to keep those committed outputs
reviewable:

- per-cell execution timings are not recorded, because they change on every run
  and would make every diff look like a content change;
- cells are executed from a clean state in notebook order, so execution counts
  always read 1, 2, 3, ... in the stored file.

Any exception in any cell fails the run: a notebook that cannot execute is a
broken narrative, not a notebook with an interesting error output.

Usage::

    python scripts/run_notebooks.py                 # all notebooks
    python scripts/run_notebooks.py 04 05           # only those matching a prefix
    python scripts/run_notebooks.py --timeout 600
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "select",
        nargs="*",
        help="optional notebook name prefixes, for example 04 or 04_balance",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="per-cell timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--kernel",
        default="python3",
        help="kernel name to execute with (default: python3)",
    )
    return parser.parse_args()


def selected_notebooks(select: list[str]) -> list[Path]:
    """Return the notebooks to execute, in lexical order."""
    notebooks = sorted(NOTEBOOKS.glob("*.ipynb"))
    if not notebooks:
        raise RuntimeError("No notebooks found. Run scripts/create_notebooks.py first.")
    if not select:
        return notebooks
    chosen = [path for path in notebooks if path.name.startswith(tuple(select))]
    if not chosen:
        raise RuntimeError(f"No notebook matches {select}. Available: {[p.name for p in notebooks]}")
    return chosen


def execute(path: Path, *, timeout: int, kernel: str) -> tuple[nbformat.NotebookNode, float]:
    """Execute one notebook in place, returning it and the wall-clock seconds taken."""
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=timeout,
        kernel_name=kernel,
        # The repository root is the working directory, so notebook paths such as
        # data/processed resolve the same way they do for scripts/run_pipeline.py.
        resources={"metadata": {"path": str(ROOT)}},
        record_timing=False,
    )
    started = time.perf_counter()
    client.execute()
    elapsed = time.perf_counter() - started
    nbformat.write(notebook, path)
    return notebook, elapsed


def main() -> None:
    """Execute the selected notebooks and report a per-notebook summary."""
    args = parse_args()
    notebooks = selected_notebooks(args.select)
    total = 0.0
    for path in notebooks:
        notebook, elapsed = execute(path, timeout=args.timeout, kernel=args.kernel)
        total += elapsed
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        with_output = [cell for cell in code_cells if cell.get("outputs")]
        print(
            f"executed {path.name:<40} "
            f"{len(code_cells):>2} code cells, "
            f"{len(with_output):>2} with output, "
            f"{elapsed:>6.1f}s"
        )
    print(f"{len(notebooks)} notebooks executed in {total:.1f}s")


if __name__ == "__main__":
    main()

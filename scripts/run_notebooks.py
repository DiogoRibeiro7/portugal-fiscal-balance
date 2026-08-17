#!/usr/bin/env python
"""Execute all notebooks in lexical order and persist their outputs in place."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def main() -> None:
    notebooks = sorted(NOTEBOOKS.glob("*.ipynb"))
    if not notebooks:
        raise RuntimeError("No notebooks found. Run scripts/create_notebooks.py first.")
    for path in notebooks:
        nb = nbformat.read(path, as_version=4)
        client = NotebookClient(
            nb,
            timeout=180,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
        )
        client.execute()
        nbformat.write(nb, path)
        print(f"executed {path.name}")


if __name__ == "__main__":
    main()

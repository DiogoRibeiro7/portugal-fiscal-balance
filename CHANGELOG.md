# Changelog

All notable changes to this repository will be documented in this file.

This project follows semantic versioning for repository releases where practical.

## [Unreleased]

### Added

- Notebook narrative contract: every notebook now states its purpose, inputs, outputs and
  methodology reference, prints its identity or tolerance checks, closes with an explicit
  interpretation-limits section, and links to the adjacent stages.
- Inline figures in the notebooks, built by the same functions that write
  `outputs/figures/`, so a notebook chart cannot drift from the persisted file.
- Three persisted figures: subsector contributions, balance sign states and detailed
  account coverage.
- `make notebooks-build`, `make lint` and `make typecheck` targets; notebook selection by
  name prefix in `scripts/run_notebooks.py`.

### Changed

- `analysis/figures.py` builders return a Matplotlib figure instead of writing a file, with
  `save_figure` as the only filesystem entry point, a shared house style, and a fixed
  categorical palette validated for colour-vision-deficiency separation.
- Figures reindex source gaps to `NaN`, so no line is drawn across the missing 1996-1999
  subsector accounts.
- Generated notebooks use deterministic cell identifiers and are executed without per-cell
  timing metadata, which keeps committed notebook diffs readable.
- Sector-to-column and sector-label mappings are defined once in `schemas.py` instead of
  being repeated in three analysis modules.

## [0.2.0] - 2026-08-17

### Added

- Reproducible pipeline for Portugal fiscal-balance analysis, 1977-2025.
- Processed datasets, analysis tables, figures, generated report and regression tests.
- Zenodo metadata for release archiving.

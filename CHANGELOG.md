# Changelog

All notable changes to this repository will be documented in this file.

This project follows semantic versioning for repository releases where practical.

## [Unreleased]

### Added

- Report: a results-at-a-glance section whose residual rows double as an audit trail, a
  source-provenance table carrying SHA-256 prefixes, the quantified 1995 vintage revision,
  a transition-probability matrix, a recent-period decomposition, and an appendix mapping
  every section to its notebook and persisted artefact.
- Report: table of contents, captioned and cross-referenced tables and figures, PDF
  metadata, and the repository version on the title page.
- `tests/test_report.py`, guarding that every included figure exists, every persisted
  figure is used, every cross-reference resolves, headline numbers match the panel, and no
  raw column identifier leaks into a table.
- `make pdf` for building the PDF from the generated LaTeX.

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

- Report rendering split into `reporting/latex.py` (escaping, number formatting, float
  environments) and `reporting/render.py` (artefact loading and document structure). Table
  headers are LaTeX-ready while cell values are escaped, numeric columns are right-aligned
  from their dtype, years carry no thousands separator, a column no longer mixes integer
  and decimal formatting, and a table is shrunk only when it would otherwise overflow.
- Report figures in prose now use the same formatter as the tables, so a rounded value in
  the text can no longer disagree with the same value in a table.
- The summary JSON reports `latest_year` including its year rather than a hard-coded
  `latest_2025`, and the report derives the final year from each artefact separately.
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

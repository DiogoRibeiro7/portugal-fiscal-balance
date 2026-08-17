# Changelog

All notable changes to this repository will be documented in this file.

This project follows semantic versioning for repository releases where practical.

## [Unreleased]

### Added

- Regime-split persistence (`persistence_by_regime.csv`). The pooled mean straddles the 1995
  splice and describes neither regime: the aggregate balance averages -6.43% of GDP over
  1977-1994 and -4.04% over 1995-2025, against a pooled -4.92%. Sign counts are reported on
  the same basis; runs are not recomputed per regime, because a run truncated at a window
  boundary reports the length of the window.
- Change-point robustness. `structural_breaks.csv` gains a BIC margin over the next-best
  break count, and three new artefacts quantify how firm a date is: a BIC ladder scoring
  every admissible count including zero, a sensitivity grid over `min_segment` in {4,5,6,7}
  crossed with `max_breaks` in {1,2,3}, and a stability summary reporting the share of the
  grid that returns the modal set of dates. Break years are now stated as candidates, and
  the report names the series where the preferred specification disagrees with the grid.
- `largest_balance_movements.csv`: the five largest annual improvements and deteriorations,
  ranked on the GDP-scaled change rather than nominal euro, with the subsector accounting
  for most of each move and the revenue and expenditure changes that composed it. The
  residual between the canonical and account-panel measures of the same change is carried
  as a column rather than reconciled away.
- GDP-scaled columns on `balance_change_attribution.csv`. They share one denominator, so the
  decomposition stays exact; this is not the change in the balance ratio.
- `primary_balance_sign_summary.csv`. Central Government records a negative B.9 in all 45
  observed years while its primary balance is positive in 15 of them, spread across the
  panel rather than confined to the recent period, so the permanently negative headline
  cannot be read as a permanent underlying deficit.
- `ssf_accounting_boundary_comparison.csv`: the ESA 2010 Social Security balance beside the
  CFP budget-system total. The two are never added or reconciled; the difference is non-zero
  in every overlapping year, which is why the two must not be used interchangeably.
- `source_validation_summary.csv`, collecting every cross-check in one unit and separating
  identity closure from source agreement. The identities close to the sources' 1 M EUR
  rounding while the largest source disagreement is a Central Government difference of about
  67 M EUR, so neither test substitutes for the other.
- `vintage_status` on the canonical balance panel, carrying the publisher's provisional flag
  through instead of dropping it, plus a per-source `vintage` in `config/sources.yml`. The
  report now states which years are provisional.
- Five persisted figures: the historical attribution window, General Government revenue and
  expenditure changes, the CFP Social Security budget systems, the two Social Security
  accounting boundaries, and the PORDATA-versus-CFP source differences.
- Report test guarding against unescaped `%`, which starts a LaTeX comment and silently
  deletes the rest of the line while still compiling.

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
  being repeated in three analysis modules. The two statistical regimes and their
  presentation labels join them there.
- The year-to-year attribution figure is drawn as two panels, 1978-1994 and 1996-2025, with
  the window written into each title. It previously drew 2000-2025 silently: a stacked bar
  chart gives the reader no way to tell that years are missing from its ends, and a single
  panel spanning 1995 would place a vintage revision among the economic movements. The
  revenue-and-expenditure change figure now requires its window for the same reason.
- The report ranks annual movements on the GDP-scaled change. The nominal ranking is
  dominated by recency, and the scaled ranking surfaces 1980, 1981, 1984 and 1986 as
  episodes comparable in size to the recent ones.
- The macroeconomic co-movement regressions moved to an appendix, with the four specific
  weaknesses stated: the dependent variable and regressor share a construction through
  nominal GDP, nominal growth conflates real growth and inflation, the fits are very low and
  insignificant, and the labour specification rests on eighteen observations. Nothing in the
  report body depends on them.
- The `PDF` is committed rather than gitignored, so the readable output is available from the
  repository without a LaTeX installation.

## [0.2.0] - 2026-08-17

### Added

- Reproducible pipeline for Portugal fiscal-balance analysis, 1977-2025.
- Processed datasets, analysis tables, figures, generated report and regression tests.
- Zenodo metadata for release archiving.

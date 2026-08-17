# Changelog

All notable changes to this repository will be documented in this file.

This project follows semantic versioning for repository releases where practical.

## [Unreleased]

### Added

- **European benchmark.** Eurostat `gov_10a_main` B.9 by subsector, 1995-2025, bundled as a
  raw source and read from the snapshot. The same definitions are applied to 28 reporters,
  which answers the one question a single-country study cannot: whether Portugal's
  composition is unusual. The answer is not uniform, and that is the point. A permanently
  deficit-running central tier is common — 9 reporters record one in every year they cover —
  so the Central Government finding is weaker in context than in isolation. Portugal's
  Social Security surplus is in the upper tail on both frequency (93.5% of years against a
  median of 68.9%) and size (0.71% of GDP against 0.17%). Its median offset ratio is
  ordinary. And on the sharpest comparison, the composition of a surplus year, Portugal is
  the only reporter whose every aggregate-surplus year combines that surplus with a negative
  non-Social-Security balance — a composition found in 27% of European surplus years, though
  Portugal's own count is 4, which is stated beside the claim.
- Three construction choices are enforced rather than assumed. The non-Social-Security
  aggregate includes state government, so federal reporters are treated consistently with
  unitary ones and their identity closes. Ratios are computed in national currency, because
  the published shares of GDP carry one decimal and are an unusable ratio denominator; the
  offset ratio additionally requires a denominator of at least 0.5% of GDP. And a reporter
  needs fifteen complete years before its frequencies are compared with a reporter covering
  thirty.
- Eurostat's Portuguese rows agree with the domestic panel to rounding, so the benchmark
  source doubles as an independent check on the whole extraction.
- `sources/eurostat.py`, `analysis/benchmark.py`, two figures, a benchmark section in both
  documents, and notebook `15_european_benchmark`.

- `ssf_balance_change_decomposition.csv`: each annual change in the Social Security balance
  split into the account movements that produced it — contributions, other revenue, social
  transfers and other expenditure. Every term is reported both as a raw change and as a
  *contribution*, carrying the sign with which it enters the balance, so the four
  contributions sum to the balance change. This is what the second research question now
  answers: the earlier section located the balance without decomposing its movement.
- A figure for that decomposition, in which expenditure layers sit below zero because they
  reduce the balance. Plotting raw expenditure changes would put a bar above zero for a
  movement that worsened the balance.
- A LaTeX job in CI that compiles both documents, runs BibTeX and fails on any unresolved
  citation or reference. The Python tests check document structure with regular expressions
  and cannot catch a missing package, a bibliography error or a real LaTeX failure.

- `paper/`: a scientific manuscript, separate from the technical report. It has a research
  question, a literature position, a stated contribution and an argument, and it carries
  only the evidence that argument needs; the report remains the place to look for
  everything else the pipeline computes.
- A generated-input mechanism so the manuscript can be authored without transcribing
  numbers. `reporting/paper.py` writes `paper/generated/macros.tex`, exposing every
  quantity the prose may cite as a LaTeX command, plus the manuscript's tables. A sentence
  reads `\SsfPositiveYears\ of \PanelYears\ years` rather than `43 of 49`, so a stale
  number cannot survive in the text, and a macro that ceases to exist fails the build
  instead of rendering as nothing. Figures are read from `outputs/figures/` rather than
  copied, so the paper, the report and the notebooks cannot disagree about a chart.
- `paper/references.bib`, with every entry checked at the publisher, RePEc or the issuing
  institution rather than taken from a secondary citation.
- `tests/test_paper.py`, enforcing the split between authored and generated content: every
  macro the prose cites is defined, every generated macro is used, no digit-grouped money
  value appears in authored text, and every include, figure, citation and cross-reference
  resolves. The manuscript is also checked for a build date, which would make the
  committed PDF change on every rebuild.
- `make paper`.

### Fixed

- The subsector-contributions figure caption claimed the visible column height equals the
  arithmetic sum of the layers. It does not: positive and negative components stack away from
  zero independently, so the visible span is the sum of the *absolute* contributions, and the
  General Government line is the algebraic sum. Corrected in both documents.
- `largest_balance_movements.csv` reported aggregate revenue and expenditure changes beside a
  subsector attribution, inviting the reader to connect quantities describing different
  entities. The attribution is now hierarchical: the revenue and expenditure split is of the
  subsector that dominates the move. Column labels changed from "From revenue"/"From
  expenditure", which implied contributions to the balance, to explicit change and
  contribution columns.
- The same table ranked historical and modern episodes in one list, comparing two
  methodologies by size — the practice the rest of the analysis refuses for magnitudes.
  Ranking now happens within each regime.
- Figure 1 drew an unbroken line across the 1995 splice while its caption said the two sides
  are not chained. The line now breaks at the boundary, so the discontinuity is visible
  rather than only asserted.
- The claim that a balance's sign does not depend on the vintage was too general: a revision
  can move a small balance across zero. Replaced with the empirical check — sign
  classifications are unchanged across both source overlaps this panel retains.
- Dropped "underlying" as a description of the primary balance. It removes interest and
  nothing else, and the term suggests a structural or cyclically adjusted measure that is
  never computed here.
- The four positive-balance years were presented as three findings. Given a positive
  aggregate and a negative non-Social-Security balance, the remaining conditions follow from
  the identity; only the negative non-Social-Security balance is empirical content.
- The change-point criterion is now described as a BIC-style penalized criterion, with the
  penalty stated, and attributed to the literature it comes from (Yao 1988; Bai and Perron
  1998). Presenting it as "the BIC" glossed over the fact that several penalties exist.
- "Only the headline figure is routinely reported" overstated the case: the Portuguese Public
  Finance Council publishes and discusses the subsector balances. Softened, and the
  manuscript now states explicitly that the Council already identifies the recent role of the
  Social Security Funds, so the contribution is the long-run systematic treatment rather than
  the recent observation.
- Shortened the manuscript abstract and concentrated the epistemological caveats in the
  framework and conclusion instead of restating them in every results subsection.
- `paper/README.md` referred to `main.tex` in its directory tree after the file was renamed
  to `paper.tex`.

- Regime-split persistence (`persistence_by_regime.csv`). The pooled mean straddles the 1995
  splice and describes neither regime: the aggregate balance averages -6.43% of GDP over
  1977-1994 and -4.04% over 1995-2025, against a pooled -4.91%. Sign counts are reported on
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

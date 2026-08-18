# Changelog

All notable changes to this repository will be documented in this file.

This project follows semantic versioning for repository releases where practical.

## [Unreleased]

### Changed

- **CI no longer compiles LaTeX.** The job installed a full texlive toolchain on every
  push, which put a large download from an apt mirror on the critical path of every
  commit. It kept CI red for nineteen consecutive commits on a missing `lmodern.sty`,
  and then hung for twenty-three minutes on the install step during the 0.3.0 release.
  A permanently red pipeline is worse than no pipeline, because it trains you to ignore
  it: the missing `types-PyYAML` stub went unnoticed for those same nineteen commits for
  exactly that reason. Everything that tests code now finishes in under a minute.
- What the job checked was not worthless, so it moved rather than disappearing.
  `make docs-check` hashes the committed PDFs, rebuilds both from scratch and fails if
  either hash moved, which is what keeps the pdfTeX metadata suppression honest. It is
  now a documented release gate in `RELEASE.md`, run where the compile was happening
  anyway. `make docs` builds both documents in one step.
- The structural checks the LaTeX job duplicated are unaffected: `tests/test_paper.py`
  and `tests/test_report.py` still verify that every macro resolves, every citation has
  an entry, every figure exists, every cross-reference resolves and no unescaped `%`
  silently comments out a line. What is given up is catching a missing LaTeX package or
  a BibTeX error without compiling, and compiling locally is required anyway because
  both PDFs are tracked.

## [0.3.0] - 2026-08-18

This release turns a reproducible pipeline into a reproducible *argument*. It adds a
scientific manuscript alongside the technical report, three new bundled sources, a
European comparison set and a link from the Social Security accounts to a quantity
outside them. It also records, in detail, the errors four rounds of review and one
self-review found in the work as it went.

### Added

- **`paper/`: a scientific manuscript, separate from the technical report.** It has a
  research question, a literature position, a stated contribution and an argument, and it
  carries only the evidence that argument needs. The report remains the place to look for
  everything else the pipeline computes.
- **A generated-input mechanism, so the manuscript can be authored without transcribing
  numbers.** `reporting/paper.py` writes `paper/generated/macros.tex`, exposing every
  quantity the prose may cite as a LaTeX command, plus the manuscript's tables. A sentence
  reads `\SsfPositiveYears\ of \PanelYears\ years` rather than `43 of 49`, so a stale
  number cannot survive in the text, and a macro that ceases to exist fails the build
  rather than rendering as nothing. Figures are read from `outputs/figures/` rather than
  copied, so the paper, the report and the notebooks cannot disagree about a chart.
  `tests/test_paper.py` enforces the split: every cited macro is defined, every generated
  macro is used, no digit-grouped money value appears in authored text, and every include,
  figure, citation and cross-reference resolves.
- **`paper/references.bib`**, with every entry checked at the publisher, RePEc or the
  issuing institution rather than taken from a secondary citation.

- **A European benchmark.** Eurostat `gov_10a_main` B.9 by subsector, 1995-2025, bundled
  as a raw source. The same definitions applied to 28 reporters answer the one question a
  single-country study cannot: whether Portugal's composition is unusual. The answer is
  not uniform, and that is the point. A permanently deficit-running central tier is common
  — 9 reporters record one in every year they cover — so the Central Government finding is
  weaker in context than in isolation. Portugal's Social Security surplus is in the upper
  tail on both frequency (93.5% of years against a median of 68.9%) and size (0.71% of GDP
  against 0.17%). Its median offset ratio is ordinary. And on the sharpest comparison, the
  composition of a surplus year, Portugal is the only reporter whose every aggregate-surplus
  year combines that surplus with a negative non-Social-Security balance — a composition
  found in 27% of European surplus years, though Portugal's own count is 4, which is stated
  beside the claim.
- Three benchmark construction choices are enforced rather than assumed. The
  non-Social-Security aggregate includes state government, so federal reporters are treated
  consistently with unitary ones and their identity closes; the tier is required of any
  country that reports it anywhere in its record, and not required of countries that have
  none. Ratios are computed in national currency, because the published shares of GDP carry
  one decimal and are an unusable ratio denominator. And a reporter needs fifteen complete
  years before its frequencies are compared with a reporter covering thirty.
- Two benchmark sensitivities, because both conclusions they support rested on a
  researcher's choice. Sweeping the offset denominator floor from 0.25% to 1.00% of GDP
  moves Portugal's percentile only between 50 and 57. Weighting the surplus-year composition
  by country rather than by country-year gives a median of 25% against the pooled 27%, with
  Portugal at the 95th percentile on both.
- Eurostat's Portuguese rows agree with the domestic panel to rounding, so the benchmark
  source doubles as an independent check on the whole extraction.

- **The contribution base.** Social Security contributions are related to the aggregate
  employee wage bill that is their principal observable reference base — a reference base
  and not the integral base of the levy, since recorded contributions include imputed
  amounts and bases the wage bill does not measure. This is what takes the Social Security
  results from an accounting location to a named quantity outside the fiscal accounts.
  Writing the contributions-to-wage-bill ratio as tau = C/W, the change in contributions
  decomposes exactly into a wage-bill component, a ratio component and their interaction;
  a second and separate application of the same identity decomposes the wage bill itself
  into employment, average wages and their interaction. Both close to numerical precision.
  The interaction terms are carried rather than dropped or shared, because either would
  make the decomposition inexact while looking tidier.
- Of the 2,468 M EUR rise in contributions in 2025, 1,870 M EUR is the wage-bill component,
  560 M EUR the ratio component and 38 M EUR their interaction. Separately, the wage bill
  rose by 7,196 M EUR: 4,842 M EUR from higher average wages, 2,253 M EUR from more
  employees and 102 M EUR of interaction. The two identities share a factor but not a
  total. The crises are where the mechanism is clearest: in the austerity years employment
  and wages fall together, while in 2020 they move in opposite directions, leaving the wage
  bill flat and contributions rising on the ratio alone.
- A symmetric alternative (`contribution_symmetric_decomposition.csv`), which evaluates
  each factor at the midpoint of the two years and is exact in two terms rather than three.
  Each factor differs from its counterpart in the exact form by exactly half the
  interaction, which is tested rather than claimed, so the reading does not rest on the
  convention.
- The companion regression: the change in contributions on the change in the wage bill,
  over 25 adjacent-year pairs, slope 0.248 with a HAC standard error of 0.022 and an
  R-squared of 0.926, against a mean ratio of 0.221. A second row keeps the pair straddling
  the 1995-to-2000 subsector gap and is flagged as a diagnostic: that one contaminated
  observation moves the slope to 0.133, collapses the fit to 0.396 and takes the coefficient
  past conventional significance. It is the clearest argument in the repository for the gap
  guard applied everywhere else.
- Two new bundled sources: wages and salaries with compensation of employees, and employees
  with total employment, both from the Portuguese national accounts compiled by INE and
  taken through the Eurostat dissemination API. Wages and salaries (D.11) is the base rather
  than compensation of employees (D.1), because D.1 already contains employers' social
  contributions and would place part of the numerator inside the denominator.

- **Component-level episode attribution.** `account_component_changes.csv` decomposes each
  annual revenue and expenditure change into its components, and
  `episode_component_attribution.csv` names the three largest component movements behind
  each ranked episode, for the subsector that dominates it. All three levels of the
  attribution — aggregate, subsector, that subsector's accounts — describe one entity. The
  component view separates episodes the totals make look alike: 2009 is dominated by taxes
  falling 4,248 M EUR, a revenue collapse rather than an expenditure surge; 2011 by capital
  expenditure falling 4,594 M EUR; 2021 by revenue components throughout.
- The two source families are not forced onto a common scheme. The modern workbooks
  separate four revenue and seven expenditure components, the historical series only current
  from capital, and each sector-year uses the finer scheme it reports. Coarsening the modern
  period would discard real detail; assigning modern component names to historical movements
  would fabricate it.

- **`ssf_balance_change_decomposition.csv`**: each annual change in the Social Security
  balance split into the account movements that produced it — contributions, other revenue,
  social transfers and other expenditure. Every term is reported both as a raw change and as
  a *contribution*, carrying the sign with which it enters the balance, so the four sum to
  the balance change.

- **Regime-split persistence** (`persistence_by_regime.csv`). The pooled mean straddles the
  1995 splice and describes neither regime: the aggregate balance averages -6.43% of GDP
  over 1977-1994 and -4.04% over 1995-2025, against a pooled -4.91%. Runs are not recomputed
  per regime, because a run truncated at a window boundary reports the length of the window.
- **Change-point robustness.** `structural_breaks.csv` gains a BIC margin over the next-best
  break count, and three artefacts quantify how firm a date is: a BIC ladder scoring every
  admissible count including zero, a sensitivity grid over `min_segment` in {4,5,6,7} crossed
  with `max_breaks` in {1,2,3}, and a stability summary reporting the share of the grid
  returning the modal set of dates. Break years are stated as candidates throughout.
- **`largest_balance_movements.csv`**: the five largest annual movements inside each regime,
  ranked on the GDP-scaled change rather than nominal euro, with the subsector accounting for
  most of each move and the revenue and expenditure changes that composed it.
- **`primary_balance_sign_summary.csv`** and its per-regime companion. Central Government
  records a negative B.9 in all 45 observed years while its primary balance is positive in
  15 of them — 9 of 19 over 1977-1995 and 6 of 26 over 2000-2025 — so the permanently
  negative headline cannot be read as a permanent underlying deficit.
- **`ssf_accounting_boundary_comparison.csv`**: the ESA 2010 Social Security balance beside
  the CFP budget-system total. The two are never added or reconciled; the difference is
  non-zero in every overlapping year.
- **`source_validation_summary.csv`**, collecting every cross-check in one unit and
  separating identity closure from source agreement. The identities close to the sources'
  1 M EUR rounding while the largest source disagreement is a Central Government difference
  of about 67 M EUR, so neither test substitutes for the other.
- `vintage_status` on the canonical balance panel, carrying the publisher's provisional flag
  through instead of dropping it, plus a per-source `vintage` in `config/sources.yml`.

- **The report as a LaTeX document**: table of contents, captioned and cross-referenced
  tables and figures, PDF metadata, the repository version on the title page, a
  results-at-a-glance section whose residual rows double as an audit trail, a
  source-provenance table carrying SHA-256 prefixes, the quantified 1995 vintage revision,
  a transition-probability matrix, and an appendix mapping every section to its notebook and
  persisted artefact. `tests/test_report.py` guards that every included figure exists, every
  persisted figure is used, every cross-reference resolves, headline numbers match the panel,
  and no raw column identifier leaks into a table.
- **Notebook narrative contract**: every notebook states its purpose, inputs, outputs and
  methodology reference, prints its identity or tolerance checks, closes with an explicit
  interpretation-limits section, and links to the adjacent stages. Inline figures are built
  by the same functions that write `outputs/figures/`, so a notebook chart cannot drift from
  the persisted file.
- **A LaTeX job in CI** that compiles both documents, runs BibTeX, fails on any unresolved
  citation or reference, and rebuilds them to require byte-identical PDFs. The Python tests
  check document structure with regular expressions and cannot catch a missing package, a
  bibliography error or a real LaTeX failure.
- Eleven persisted figures, `make paper`, `make pdf`, `make notebooks-build`, `make lint`
  and `make typecheck`.

### Changed

- The report body now carries the composition argument and nothing else. The
  fixed-capital-formation diagnostic, the debt and stock-flow reconciliation, the
  intergovernmental-transfer sensitivity and the co-movement regressions move to appendices.
  Each answers a question adjacent to the report's own, and each is retained in full with a
  stated reason for being where it is: placing a non-official indicator among B.9 results
  invites it being read as one.
- The contribution base sits immediately after the Social Security section, since it answers
  the question that section raises.
- Report rendering is split into `reporting/latex.py` (escaping, number formatting, float
  environments) and `reporting/render.py` (artefact loading and document structure). Table
  headers are LaTeX-ready while cell values are escaped, numeric columns are right-aligned
  from their dtype, years carry no thousands separator, and a table is shrunk only when it
  would otherwise overflow. Report figures in prose use the same formatter as the tables, so
  a rounded value in the text cannot disagree with the same value in a table.
- `analysis/figures.py` builders return a Matplotlib figure instead of writing a file, with
  `save_figure` as the only filesystem entry point, a shared house style, and a fixed
  categorical palette validated for colour-vision-deficiency separation. Figures reindex
  source gaps to `NaN`, so no line is drawn across the missing 1996-1999 subsector accounts.
- The year-to-year attribution figure is drawn as two panels, 1978-1994 and 1996-2025, with
  the window written into each title. It previously drew 2000-2025 silently: a stacked bar
  chart gives the reader no way to tell that years are missing from its ends, and a single
  panel spanning 1995 would place a vintage revision among the economic movements.
- Annual movements are ranked on the GDP-scaled change. The nominal ranking is dominated by
  recency; the scaled ranking surfaces 1980, 1981, 1984 and 1986 as episodes comparable in
  size to the recent ones.
- Sector-to-column and sector-label mappings are defined once in `schemas.py` instead of
  being repeated across analysis modules, joined there by the statistical regimes, their
  presentation labels and the source-family labels.
- Generated notebooks use deterministic cell identifiers and are executed without per-cell
  timing metadata, which keeps committed notebook diffs readable.
- The summary JSON reports `latest_year` including its year rather than a hard-coded
  `latest_2025`, and the report derives the final year from each artefact separately.
- The compiled PDFs are committed rather than gitignored, so the readable output is
  available from the repository without a LaTeX installation.

### Fixed

- **The committed PDFs were not byte-reproducible.** pdfTeX stamps each build with a
  creation date, a modification date and a random file identifier, so two builds from
  identical inputs differed as files while being identical as documents. Every rebuild
  dirtied the working tree and quietly falsified the claim that the pipeline is
  deterministic. Both preambles now suppress that metadata and CI enforces the hashes match.
  Found by testing the determinism claim rather than trusting it.
- **CI was red on nineteen consecutive pushes**, on two causes a green local run hid. Mypy
  failed on a missing PyYAML stub: `render.py` reads `config/sources.yml`, and
  `types-PyYAML` happened to be installed in the development virtualenv but was never
  declared, so the lockfile CI builds from never had it. The LaTeX job failed on
  `lmodern.sty`, which `--no-install-recommends` does not pull in.

- **A conflation of two identities.** The conclusion, the changelog and the data dictionary
  described the employment and average-wage terms as sitting "within" the wage-bill component
  of the contribution change. They do not: they sum to the change in the wage bill, 7,196
  M EUR in 2025, not to the 1,870 M EUR wage-bill component of the 2,468 M EUR contribution
  change. They are now stated separately, carried in two tables, and a test asserts the
  totals differ.
- **tau is no longer called an effective *rate*,** in prose or in column names, and the
  wage bill is described as a reference base rather than the integral base of the levy.
  Calling the second term a "rate effect" invited reading a movement in it as a change in
  the statutory levy.
- **A table stated year ranges false for six of its eight rows.** The regime split is keyed
  two ways in the pipeline — by the window it covers and by the source family that produced
  it — and the family key was labelled with a fixed window. A family does not span the same
  years in every sector: General Government carries detailed accounts continuously, the three
  subsectors carry them for 1977-1995 and 2000-2025 only. The same error had reached the
  abstract, introduction, results and conclusion, which described those windows as "before
  the 1995 splice" and "after it".
- **Splice discipline applied to statistics that had escaped it.** The
  General-Government-to-Central-Government correlation is reported inside each regime (0.973
  historical, 0.976 modern) and the pooled macro deleted, so the manuscript cannot cite a
  correlation computed through a vintage change. Primary-balance counts and the interest
  burden are split the same way. No extreme is selected across the two regimes: the "largest
  single improvement" and "largest deterioration" of the whole panel are replaced by
  per-regime extremes.
- **"The pattern across the recent years is the same in each: contributions are the largest
  positive term and social transfers the largest negative one."** 2020 contradicts both
  halves in the very table the sentence cites. The claim is scoped and the exception named.
- **The pooled interest mean was said to describe the historical regime better than the
  modern one.** It is the other way round: 4.17% of GDP sits 1.35 points from the historical
  5.52% and 0.98 from the modern 3.19%.
- **Four data values were typed by hand into a manuscript whose stated contract forbids it.**
  The nominal-GDP fits and the bridged-gap diagnostic are now computed, persisted and cited
  as macros.
- **An internal contradiction about the nominal-GDP specification.** The robustness section
  said it was "deliberately not part of this paper's evidence"; the contribution-base section
  then cited its fits as the comparison justifying the new specification. It is now admitted
  for exactly that one purpose, and the purpose is stated. "An order of magnitude tighter"
  appeared twice and was wrong both times: 0.926 against a highest comparator of 0.175 is
  roughly five times.
- The vintage paragraph claimed the bundled files "are the April 2026 releases". The eight
  sources range from 2023-12 to 2026-08.

- `largest_balance_movements.csv` reported aggregate revenue and expenditure changes beside
  a subsector attribution, inviting the reader to connect quantities describing different
  entities. The attribution is now hierarchical. The same table ranked historical and modern
  episodes in one list, comparing two methodologies by size — the practice the rest of the
  analysis refuses for magnitudes.
- The subsector-contributions figure caption claimed the visible column height equals the
  arithmetic sum of the layers. It does not: positive and negative components stack away
  from zero independently, so the visible span is the sum of the *absolute* contributions
  and the General Government line is the algebraic sum.
- Figure 1 drew an unbroken line across the 1995 splice while its caption said the two sides
  are not chained. The line now breaks at the boundary.
- The claim that a balance's sign does not depend on the vintage was too general: a revision
  can move a small balance across zero. Replaced with the empirical check — sign
  classifications are unchanged across both source overlaps this panel retains.
- Dropped "underlying" as a description of the primary balance. It removes interest and
  nothing else, and the term suggests a structural or cyclically adjusted measure never
  computed here.
- The four positive-balance years were presented as three findings. Given a positive
  aggregate and a negative non-Social-Security balance, the remaining conditions follow from
  the identity; only the negative non-Social-Security balance is empirical content.
- The change-point criterion is described as a BIC-style penalized criterion, with the
  penalty stated and attributed to the literature it comes from (Yao 1988; Bai and Perron
  1998). Presenting it as "the BIC" glossed over the fact that several penalties exist.
- The introduction announced six contributions and listed nine; regrouped into four. It also
  said separating the movement in contributions "would require a model of the contribution
  base ... that this paper does not build", contradicting the section that builds it.
- "Only the headline figure is routinely reported" overstated the case: the Portuguese Public
  Finance Council publishes and discusses the subsector balances. The manuscript now states
  explicitly that the Council already identifies the recent role of the Social Security Funds,
  so the contribution is the long-run systematic treatment rather than the recent observation.
- The regression interpretation was too strong. A slope near the mean ratio is consistent
  with a stable ratio component; it is not implied by the identity, which would require the
  ratio and interaction terms to be uncorrelated with the wage-bill change.
- The European benchmark treated a missing S.1312 as a zero contribution even for countries
  that operate a state tier, while still marking the year complete. No such country-year
  exists in the current vintage, so no published result changes, but the contract was wrong.
- A data-dictionary block carried literal control characters where LaTeX escapes were
  intended, and `paper/README.md` referred to a `main.tex` that does not exist.
- A report test now guards against unescaped `%`, which starts a LaTeX comment and silently
  deletes the rest of the line while still compiling.

## [0.2.0] - 2026-08-17

### Added

- Reproducible pipeline for Portugal fiscal-balance analysis, 1977-2025.
- Processed datasets, analysis tables, figures, generated report and regression tests.
- Zenodo metadata for release archiving.

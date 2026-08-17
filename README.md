# Portugal Fiscal Balance, 1977–2025

[![CI](https://github.com/DiogoRibeiro7/portugal-fiscal-balance/actions/workflows/ci.yml/badge.svg)](https://github.com/DiogoRibeiro7/portugal-fiscal-balance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

A reproducible empirical repository for analysing how Portugal's General Government balance is formed across:

- Central Government;
- Regional and Local Government;
- Social Security Funds.

The repository is deliberately restricted to accounting, statistical and economic analysis. It does not infer intent, assign responsibility, or attach normative conclusions to fiscal outcomes.

## Project resources

- Methodology: `METHODOLOGY.md`
- Data dictionary: `DATA_DICTIONARY.md`
- Generated report: `report/report.tex`
- Contribution guide: `CONTRIBUTING.md`
- Citation metadata: `CITATION.cff` and `.zenodo.json`
- Release checklist: `RELEASE.md`

## Core identity

The main annual identity is

\[
B^{GG}_t = B^{C}_t + B^{RL}_t + B^{SSF}_t,
\]

where `B` is net lending (+) / net borrowing (-), corresponding to B.9 in national accounts.

## Analysis scope

The executed pipeline includes:

1. long-run subsector balance decomposition, 1977–2025;
2. exact year-to-year balance attribution;
3. revenue/expenditure decomposition;
4. sign persistence, run lengths and transition probabilities;
5. conservative structural mean-shift detection, separated around the known 1995 statistical splice;
6. Social Security Funds revenue composition and internal system balances;
7. historical intergovernmental-transfer sensitivity;
8. primary balance and interest decomposition;
9. fixed-capital-formation diagnostic;
10. debt and stock-flow adjustment reconciliation;
11. descriptive nominal-GDP co-movement regressions with HAC standard errors;
12. a historical SSF/employment/unemployment co-movement model for 1978–1995;
13. automatic generation of the final English report from persisted analysis outputs.

## Data layers

```text
data/raw/         Official source files, immutable in normal use
data/interim/     Source-specific extracted CSVs and overlap checks
data/processed/   Canonical analysis-ready panels
outputs/tables/   Calculated tables and statistical results
outputs/metrics/  Validation summaries and source hashes
outputs/figures/  Figures generated from processed results
report/           Technical report, generated end to end from persisted outputs
paper/            Scientific manuscript: authored prose, generated tables and numbers
```

Raw files are retained and SHA-256 hashes are written to `outputs/metrics/raw_file_sha256.json`.

## Source coverage

### Banco de Portugal / INE long series

Used for the historical segment. The workbook contains sector accounts, B.9 balances, transfers, GDP and historical labour-market series. The repository uses the 1977–1995 observations relevant to the study.

### INE via PORDATA

Used as the continuous modern B.9 bridge from 1995 through 2025.

### Portuguese Public Finance Council (CFP)

The annual ESA 2010 workbooks provide:

- General Government accounts, 1995–2025;
- Central, Regional/Local and Social Security Funds accounts, 2000–2025;
- revenue and expenditure components;
- primary expenditure and interest;
- GFCF;
- Maastricht debt and stock-flow adjustments.

The CFP Social Security report data are used separately for the internal system decomposition.

## Important coverage rule

Detailed subsector account components are available in the bundled sources for:

- 1977–1995 in the historical long series;
- 2000–2025 in the modern CFP workbook.

The repository does **not** interpolate 1996–1999. Those four years remain an explicit gap for analyses that require revenue/expenditure components. The headline B.9 panel itself remains continuous from 1977 to 2025.

## Repository layout

```text
portugal-fiscal-balance/
├── config/
│   └── sources.yml
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── notebooks/
│   ├── 00_research_protocol.ipynb
│   ├── 01_extract_historical_data.ipynb
│   ├── 02_extract_modern_data.ipynb
│   ├── 03_harmonize_and_validate.ipynb
│   ├── 04_balance_decomposition.ipynb
│   ├── 05_revenue_expenditure.ipynb
│   ├── 06_year_to_year_attribution.ipynb
│   ├── 07_persistence.ipynb
│   ├── 08_structural_breaks.ipynb
│   ├── 09_social_security_mechanisms.ipynb
│   ├── 10_intergovernmental_transfers.ipynb
│   ├── 11_primary_balance.ipynb
│   ├── 12_investment_diagnostic.ipynb
│   ├── 13_debt_reconciliation.ipynb
│   ├── 14_macroeconomic_comovement.ipynb
│   └── 15_build_report.ipynb
├── src/portugal_fiscal_balance/
│   ├── sources/
│   ├── processing/
│   ├── analysis/
│   └── reporting/
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── metrics/
├── report/
│   └── report.tex
├── scripts/
│   ├── create_notebooks.py
│   ├── run_pipeline.py
│   └── run_notebooks.py
└── tests/
```

## Notebooks

The notebooks are the visible research narrative and are **committed with their executed
outputs**, including inline figures, so the whole analysis can be read on GitHub without
installing anything.

| Notebook | What it establishes |
| --- | --- |
| [00](notebooks/00_research_protocol.ipynb) | Accounting objects, source regimes, scope limits and raw-file hashes, fixed before any result is seen |
| [01](notebooks/01_extract_historical_data.ipynb) | 1977–1995 extraction from the Banco de Portugal / INE long series, with an extraction identity check |
| [02](notebooks/02_extract_modern_data.ipynb) | Modern PORDATA bridge and CFP workbooks, cross-checked against each other |
| [03](notebooks/03_harmonize_and_validate.ipynb) | Canonical 1977–2025 panel, closure residuals, the quantified 1995 revision and the 1996–1999 component gap |
| [04](notebooks/04_balance_decomposition.ipynb) | Long-run subsector decomposition and the Social Security offset metrics |
| [05](notebooks/05_revenue_expenditure.ipynb) | `B = R - E` in levels and in adjacent-year changes |
| [06](notebooks/06_year_to_year_attribution.ipynb) | Exact attribution of every annual change in the aggregate balance |
| [07](notebooks/07_persistence.ipynb) | Sign frequencies, run lengths and empirical one-year transitions |
| [08](notebooks/08_structural_breaks.ipynb) | Piecewise-constant mean shifts, detected separately per statistical regime |
| [09](notebooks/09_social_security_mechanisms.ipynb) | SSF revenue composition and the separately bounded CFP budget systems |
| [10](notebooks/10_intergovernmental_transfers.ipynb) | Mechanical transfer-reallocation sensitivity, 1977–1995 |
| [11](notebooks/11_primary_balance.ipynb) | Primary balance reconstruction and interest by sector |
| [12](notebooks/12_investment_diagnostic.ipynb) | GFCF sized against B.9 with an explicitly non-official diagnostic |
| [13](notebooks/13_debt_reconciliation.ipynb) | `ΔDebt = -B + SFA` reconciliation for the modern regime |
| [14](notebooks/14_macroeconomic_comovement.ipynb) | Descriptive HAC co-movement regressions |
| [15](notebooks/15_build_report.ipynb) | Report generation from persisted outputs only |

Every notebook follows the same contract:

- a header stating its purpose, the files it reads, the files it writes and the
  `METHODOLOGY.md` section it implements;
- an explicit identity or tolerance check wherever one exists, printed rather than assumed;
- a closing **Interpretation limits** section stating what the results are not;
- links to the previous and next stage.

Notebooks do not implement analysis. Parsers, accounting calculations, statistical
routines and plotting all live under `src/portugal_fiscal_balance/`, are type-checked and
are covered by the test suite; `tests/test_project_contract.py` enforces that no notebook
defines a reusable function or class. Notebook figures are built by the same functions the
pipeline uses to write `outputs/figures/`, so a chart in a notebook and the corresponding
file on disk cannot drift apart.

Calculated tables are always persisted to CSV as well as displayed, which allows peer
verification without reading notebook state.

The notebooks themselves are generated, so the narrative contract stays uniform and diffs
stay readable:

```bash
python scripts/create_notebooks.py                # rewrite the notebooks, without outputs
PYTHONPATH=src python scripts/run_notebooks.py    # execute them, storing outputs in place
```

`scripts/run_notebooks.py` accepts name prefixes, for example `python scripts/run_notebooks.py 04 05`.

## Reproduce

With Poetry:

```bash
poetry install
make all
```

Or directly from an environment containing the declared dependencies:

```bash
PYTHONPATH=src python scripts/run_pipeline.py
PYTHONPATH=src python scripts/run_notebooks.py
PYTHONPATH=src pytest
```

## Report

`scripts/run_pipeline.py` writes `report/report.tex`: a 22-page LaTeX report with 26
captioned tables and 15 figures. It restates persisted results and introduces no new
calculation — every number in it is read from a file under `data/processed/` or `outputs/`,
and the appendix maps each section to the notebook that produces it and the artefact it
reads.

The document opens with a results-at-a-glance table that doubles as an audit trail: the
subsector closure residual, the revenue-minus-expenditure identity error, and the debt
reconciliation residual are printed alongside the headline balances, so a defect in
extraction is visible on the first page. Each section closes with what its result is not.

Three habits shape how results are stated. Magnitudes are reported per statistical regime
rather than pooled across the 1995 splice, because the pooled mean describes neither regime.
Break dates are reported with the share of a twelve-specification grid that agrees on them,
and are called candidates rather than findings. And the co-movement regressions sit in an
appendix, with their weaknesses stated, because nothing in the body depends on them.

The built PDF is committed at `report/report.pdf`. To rebuild it (requires a LaTeX
installation):

```bash
make pdf
```

or directly, running twice so the table of contents and cross-references resolve:

```bash
cd report && pdflatex -interaction=nonstopmode report.tex && pdflatex -interaction=nonstopmode report.tex
```

`tests/test_report.py` guards the report's wiring: every included figure exists, every
persisted figure is used, every cross-reference resolves, the headline numbers match the
panel, no raw column identifier leaks into a table, and no unescaped `%` silently comments
out a line of prose.

## Paper

`paper/` holds the scientific manuscript, and it is a different product from the report.
The report is generated end to end and carries every analysis the pipeline computes. The
paper is authored — it has a research question, a literature position and an argument —
and carries only the evidence that argument needs.

The repository's contract still holds: no number is transcribed. The manuscript is split
into authored prose in `paper/sections/` and generated inputs in `paper/generated/`, which
the pipeline writes. Every quantity the prose cites is a LaTeX macro read from a persisted
artefact, so a sentence reads

```latex
The Social Security balance is positive in \SsfPositiveYears\ of \PanelYears\ years.
```

A stale number therefore cannot survive in the text, and a macro that ceases to exist
fails the build rather than rendering as nothing. Figures are read from
`outputs/figures/` rather than copied, so the paper, the report and the notebooks cannot
disagree about a chart. See [paper/README.md](paper/README.md) for the editing rules.

```bash
make pipeline    # writes paper/generated/
make paper       # compiles paper/paper.pdf
```

`tests/test_paper.py` enforces the split: every macro the prose cites is defined, every
generated macro is used, no digit-grouped money value appears in authored text, and every
include, figure and citation resolves.

## Zenodo archiving

Zenodo release metadata is defined in `.zenodo.json`; this file is the source Zenodo will prefer over `CITATION.cff` when archiving GitHub releases. The release process is documented in `RELEASE.md`. After the repository is enabled in Zenodo's GitHub integration, publishing a GitHub release will archive that release in Zenodo and assign a DOI.

## Main processed datasets

```text
data/processed/fiscal_balances_1977_2025.csv
data/processed/annual_balance_metrics_1977_2025.csv
data/processed/subsector_accounts_1977_2025.csv
data/processed/macro_panel_1977_2025.csv
```

## Main analysis tables

```text
outputs/tables/balance_change_attribution.csv
outputs/tables/largest_balance_movements.csv
outputs/tables/revenue_expenditure_change_decomposition.csv
outputs/tables/persistence_summary.csv
outputs/tables/persistence_by_regime.csv
outputs/tables/transition_probabilities.csv
outputs/tables/structural_breaks.csv
outputs/tables/structural_break_bic_ladder.csv
outputs/tables/structural_break_sensitivity.csv
outputs/tables/structural_break_stability.csv
outputs/tables/social_security_account_metrics.csv
outputs/tables/ssf_accounting_boundary_comparison.csv
outputs/tables/primary_balance_and_interest.csv
outputs/tables/primary_balance_sign_summary.csv
outputs/tables/investment_diagnostic.csv
outputs/tables/debt_stock_flow_reconciliation.csv
outputs/tables/source_validation_summary.csv
outputs/tables/nominal_gdp_balance_comovement.csv
outputs/tables/historical_ssf_labour_comovement.csv
```

See `METHODOLOGY.md` and `DATA_DICTIONARY.md` for definitions and caveats.

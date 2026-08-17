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
- Generated report: `report/report.md`
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
report/           Final report generated from persisted outputs
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
│   └── report.md
├── scripts/
│   ├── run_pipeline.py
│   └── run_notebooks.py
└── tests/
```

## Notebook design

Notebooks are the visible research narrative. They do not contain the implementation of parsers, accounting calculations, statistical routines or plotting functions. Those live under `src/portugal_fiscal_balance/`.

Calculated tables are always persisted to CSV as well as displayed in notebooks. This allows peer verification without reading notebook state.

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

The final report is written to:

```text
report/report.md
```

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
outputs/tables/revenue_expenditure_change_decomposition.csv
outputs/tables/persistence_summary.csv
outputs/tables/transition_probabilities.csv
outputs/tables/structural_breaks.csv
outputs/tables/social_security_account_metrics.csv
outputs/tables/primary_balance_and_interest.csv
outputs/tables/investment_diagnostic.csv
outputs/tables/debt_stock_flow_reconciliation.csv
outputs/tables/nominal_gdp_balance_comovement.csv
outputs/tables/historical_ssf_labour_comovement.csv
```

See `METHODOLOGY.md` and `DATA_DICTIONARY.md` for definitions and caveats.

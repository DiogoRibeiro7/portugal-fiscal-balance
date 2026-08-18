#!/usr/bin/env python
"""Create the repository's notebook narratives.

The notebooks are generated rather than hand-edited so that the visible research
narrative stays consistent: every notebook has the same header contract (purpose,
inputs, outputs, method reference), the same environment cell, an explicit
identity or tolerance check where one exists, and a stated set of interpretation
limits. Cell identifiers are deterministic, so regenerating a notebook produces a
readable diff instead of a wall of new random ids.

Notebooks display results and figures. They never define analytical functions:
parsers, accounting calculations, statistical routines and plotting all live in
``src/portugal_fiscal_balance`` and are covered by the test suite.

Usage::

    python scripts/create_notebooks.py     # write the notebooks, without outputs
    python scripts/run_notebooks.py        # execute them and store outputs in place
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"

SETUP = r'''"""Notebook environment: locate the repository and expose its data layers."""

import sys
import warnings
from pathlib import Path

import pandas as pd
from IPython.display import display

# Resolve the repository root from wherever the kernel was started, so the
# notebook works both from the repository root and from the notebooks directory.
ROOT = Path.cwd()
while not (ROOT / 'pyproject.toml').exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

PLOT_IMPORTSRAW = ROOT / 'data' / 'raw'
INTERIM = ROOT / 'data' / 'interim'
PROCESSED = ROOT / 'data' / 'processed'
TABLES = ROOT / 'outputs' / 'tables'
METRICS = ROOT / 'outputs' / 'metrics'

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
pd.set_option('display.max_columns', 80)
pd.set_option('display.width', 200)

print('repository:', ROOT.name)
print('pipeline outputs present:', (PROCESSED / 'fiscal_balances_1977_2025.csv').exists())'''

PLOT_IMPORTS = r'''%matplotlib inline

from portugal_fiscal_balance.analysis import figures

'''

LIMITS_HEADING = "## Interpretation limits"


@dataclass
class Notebook:
    """One generated notebook narrative."""

    name: str
    title: str
    purpose: str
    inputs: list[str]
    outputs: list[str]
    method: str
    cells: list[tuple[str, str]] = field(default_factory=list)
    plots: bool = True


def _header(spec: Notebook) -> str:
    """Build the standard header markdown for one notebook."""
    inputs = "\n".join(f"- `{value}`" for value in spec.inputs)
    outputs = "\n".join(f"- {value}" for value in spec.outputs)
    return (
        f"# {spec.title}\n\n"
        f"{spec.purpose}\n\n"
        f"**Reads**\n\n{inputs}\n\n"
        f"**Writes**\n\n{outputs}\n\n"
        f"**Method reference:** {spec.method}"
    )


def _footer(index: int, specs: list[Notebook]) -> str:
    """Build the navigation and reproduction footer for one notebook."""
    links = []
    if index > 0:
        previous = specs[index - 1]
        links.append(f"[Previous: {previous.title}]({previous.name})")
    if index < len(specs) - 1:
        following = specs[index + 1]
        links.append(f"[Next: {following.title}]({following.name})")
    navigation = " | ".join(links)
    return (
        "---\n\n"
        f"{navigation}\n\n"
        "Every table shown above is also persisted as CSV, so results can be checked "
        "without reading notebook state. To rebuild everything from the bundled raw "
        "sources:\n\n"
        "```bash\n"
        "poetry install\n"
        "make all\n"
        "```"
    )


def build(spec: Notebook, index: int, specs: list[Notebook]) -> nbf.NotebookNode:
    """Assemble one notebook, with deterministic cell identifiers."""
    notebook = nbf.v4.new_notebook()
    notebook.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook.metadata["language_info"] = {"name": "python", "version": "3"}

    setup = SETUP.replace("PLOT_IMPORTS", PLOT_IMPORTS if spec.plots else "")
    sequence: list[tuple[str, str]] = [
        ("md", _header(spec)),
        ("code", setup),
        *spec.cells,
        ("md", _footer(index, specs)),
    ]
    built = []
    for position, (kind, content) in enumerate(sequence):
        identifier = f"nb{index:02d}-{position:02d}"
        if kind == "md":
            built.append(nbf.v4.new_markdown_cell(content, id=identifier))
        else:
            built.append(nbf.v4.new_code_cell(content, id=identifier))
    notebook.cells = built
    return notebook


SPECS: list[Notebook] = [
    Notebook(
        name="00_research_protocol.ipynb",
        title="00. Research protocol",
        purpose=(
            "Fix the accounting objects, the source regimes and the non-interpretive scope "
            "before any result is inspected. Nothing in this notebook depends on a finding, "
            "so the analytical rules cannot be adjusted after seeing the numbers."
        ),
        inputs=[
            "config/sources.yml",
            "outputs/metrics/raw_file_sha256.json",
        ],
        outputs=["Nothing. This notebook states the protocol and inspects source metadata."],
        method="`METHODOLOGY.md` sections 1-3 and 16",
        plots=False,
        cells=[
            (
                "md",
                r"""## 1. The object of study

The primary measure is B.9, net lending (+) / net borrowing (-), for the calendar
years 1977 to 2025. The canonical decomposition is

$$B^{GG}_t = B^{C}_t + B^{RL}_t + B^{SSF}_t,$$

where the three components are Central Government, Regional and Local Government,
and Social Security Funds.

The study describes accounting contributions, temporal dynamics and statistical
relationships. It does not infer intent, assign responsibility, or attach normative
labels to fiscal outcomes. Where a metric could invite such a reading, the notebook
that produces it states what the metric is not.""",
            ),
            (
                "md",
                """## 2. Sources under version control

Each source is pinned to a local file in `data/raw`. The workbooks are parsed
programmatically; no value is transcribed by hand.""",
            ),
            (
                "code",
                r"""import yaml

config = yaml.safe_load((ROOT / 'config' / 'sources.yml').read_text(encoding='utf-8'))
sources = pd.DataFrame(config['sources']).T[['institution', 'coverage', 'local_file']]
display(sources)""",
            ),
            (
                "md",
                """## 3. Raw-source integrity

Every bundled raw file is hashed by the pipeline. A reader who obtains the same
files can confirm they are analysing identical inputs.""",
            ),
            (
                "code",
                r"""import json

hashes = json.loads((METRICS / 'raw_file_sha256.json').read_text(encoding='utf-8'))
manifest = pd.DataFrame(
    [
        {
            'file': path,
            'size_kb': round((ROOT / path).stat().st_size / 1024, 1),
            'sha256_prefix': digest[:16],
        }
        for path, digest in sorted(hashes.items())
    ]
)
display(manifest)""",
            ),
            (
                "md",
                """## 4. Data-layer contract

```text
data/raw/         official source files, immutable in normal use
data/interim/     source-specific extractions and overlap checks
data/processed/   canonical analysis-ready panels
outputs/tables/   calculated tables and statistical results
outputs/metrics/  validation summaries and source hashes
outputs/figures/  figures generated from processed results
report/           report generated from the persisted outputs only
```

A result may only enter the report if it was first written to one of those
layers. That rule is what makes the report checkable independently of the code
that produced it.""",
            ),
            (
                "code",
                r"""layers = pd.DataFrame(
    [
        {'layer': label, 'files': len(list((ROOT / relative).glob(pattern)))}
        for label, relative, pattern in [
            ('data/raw', 'data/raw', '**/*.*'),
            ('data/interim', 'data/interim', '*.csv'),
            ('data/processed', 'data/processed', '*.csv'),
            ('outputs/tables', 'outputs/tables', '*.csv'),
            ('outputs/metrics', 'outputs/metrics', '*.json'),
            ('outputs/figures', 'outputs/figures', '*.png'),
        ]
    ]
)
display(layers)""",
            ),
            (
                "md",
                """## 5. The notebook sequence

The notebooks are the visible narrative and run in lexical order: extraction,
harmonisation and validation, then one notebook per analytical question, and
finally report generation.""",
            ),
            (
                "code",
                r"""stages = []
for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
    cells = json.loads(path.read_text(encoding='utf-8'))['cells']
    heading = next(
        line
        for cell in cells
        if cell['cell_type'] == 'markdown'
        for line in cell['source']
        if line.startswith('# ')
    )
    stages.append({'notebook': path.name, 'stage': heading.removeprefix('# ').strip()})
display(pd.DataFrame(stages))""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. **1995 is a source and methodology splice**, not an economic event. Both
   vintages of 1995 are retained as a diagnostic and nothing is smoothed across
   the boundary.
2. **Detailed subsector accounts have no 1996-1999 observations.** The gap is
   left explicit rather than interpolated.
3. **Accounting identities are not causal statements.** A subsector that
   contributes arithmetically to an aggregate balance has not been shown to have
   caused it.
4. **Descriptive regressions are co-movement estimates.** Nominal GDP growth is
   not an output gap and no specification here is a structural fiscal model.""",
            ),
        ],
    ),
    Notebook(
        name="01_extract_historical_data.ipynb",
        title="01. Historical extraction: Banco de Portugal / INE",
        purpose=(
            "Extract the 1977-1995 balance, account, transfer and macro tables directly "
            "from the bundled official long-series workbook, and check that the extracted "
            "accounts satisfy revenue minus expenditure equals the balance."
        ),
        inputs=["data/raw/banco_portugal/series_longas_2023-12.xlsx"],
        outputs=[
            "`data/interim/historical_balances_1977_1995.csv`",
            "`data/interim/historical_accounts_1977_1995.csv`",
            "`data/interim/historical_intragov_transfers_1977_1995.csv`",
            "`data/interim/historical_macro_1977_1995.csv`",
        ],
        method="`METHODOLOGY.md` sections 3-4",
        cells=[
            (
                "md",
                """## 1. Parse the workbook

The historical workbook holds sector accounts, B.9 balances, intragovernmental
transfers, GDP and labour-market series across several sheets and layouts. The
parser lives in `portugal_fiscal_balance.sources.banco_portugal`, so the parsing
rules are testable and this notebook stays a narrative.""",
            ),
            (
                "code",
                r"""from portugal_fiscal_balance.io import write_csv
from portugal_fiscal_balance.sources.banco_portugal import extract_long_series

historical = extract_long_series(RAW / 'banco_portugal' / 'series_longas_2023-12.xlsx')
shapes = pd.DataFrame(
    [
        {'table': 'balances', 'rows': historical.balances.shape[0], 'columns': historical.balances.shape[1]},
        {'table': 'accounts', 'rows': historical.accounts.shape[0], 'columns': historical.accounts.shape[1]},
        {'table': 'transfers', 'rows': historical.transfers.shape[0], 'columns': historical.transfers.shape[1]},
        {'table': 'macro', 'rows': historical.macro.shape[0], 'columns': historical.macro.shape[1]},
    ]
)
display(shapes)""",
            ),
            (
                "md",
                """## 2. The historical balance panel

The four balances are reported in millions of euro alongside nominal GDP, which
makes the GDP ratios reproducible rather than copied from a published table.""",
            ),
            (
                "code",
                r"""balance_columns = [
    'year',
    'general_government_balance_m_eur',
    'central_government_balance_m_eur',
    'regional_local_balance_m_eur',
    'social_security_balance_m_eur',
    'nominal_gdp_m_eur',
]
display(historical.balances[balance_columns].tail(8).round(1))""",
            ),
            (
                "code",
                r"""figure = figures.balances_by_subsector(
    historical.balances,
    title='Historical long series: fiscal balance by subsector, 1977-1995',
    splice_year=None,
)""",
            ),
            (
                "md",
                """The 1995 observation is extracted here but is **not** used in the canonical
panel: notebook 03 takes 1995 from the modern source and keeps this vintage only
as an overlap diagnostic.

## 3. Detailed subsector accounts""",
            ),
            (
                "code",
                r"""account_columns = [
    'year',
    'sector',
    'total_revenue_m_eur',
    'total_expenditure_m_eur',
    'interest_m_eur',
    'gfcf_m_eur',
    'balance_m_eur',
]
recent_accounts = historical.accounts.loc[historical.accounts['year'].ge(1993), account_columns]
display(recent_accounts.sort_values(['sector', 'year']).round(1))""",
            ),
            (
                "md",
                """## 4. Extraction check

If the parser mapped a row incorrectly, revenue minus expenditure would stop
reproducing the published balance. The residual below is therefore an extraction
test, not an economic result.""",
            ),
            (
                "code",
                r"""identity = (
    historical.accounts.groupby('sector')['account_identity_error_m_eur']
    .apply(lambda column: column.abs().max())
    .rename('max_abs_identity_error_m_eur')
    .to_frame()
)
display(identity)
print('worst absolute account identity error (M EUR):', float(identity.max().iloc[0]))""",
            ),
            (
                "md",
                """## 5. Transfers and macro context

The transfer table supports the mechanical sensitivity in notebook 10. The macro
table supplies the historical labour-market controls used in notebook 14.""",
            ),
            (
                "code",
                r"""display(historical.transfers.loc[historical.transfers['year'].ge(1993)].round(1))
display(historical.macro.tail(6).round(3))""",
            ),
            (
                "md",
                """## 6. Persist the extraction

Extracted tables are written to `data/interim` under their source name. Keeping
extraction output separate from processed panels makes it possible to attribute a
later disagreement to a specific source.""",
            ),
            (
                "code",
                r"""write_csv(historical.balances, INTERIM / 'historical_balances_1977_1995.csv')
write_csv(historical.accounts, INTERIM / 'historical_accounts_1977_1995.csv')
write_csv(historical.transfers, INTERIM / 'historical_intragov_transfers_1977_1995.csv')
write_csv(historical.macro, INTERIM / 'historical_macro_1977_1995.csv')
print('written to', INTERIM.relative_to(ROOT))""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. These are **historical-vintage** national accounts. They are not directly
   comparable with post-1995 ESA 2010 figures, and this repository never
   calibrates one to the other.
2. The workbook is a **secondary compilation** of historical statistics. Its own
   revisions are outside the scope of this repository.
3. Labour-market series from this period are used only as descriptive controls in
   notebook 14.""",
            ),
        ],
    ),
    Notebook(
        name="02_extract_modern_data.ipynb",
        title="02. Modern extraction: INE/PORDATA and CFP",
        purpose=(
            "Load the continuous modern B.9 bridge, independently parse the CFP ESA 2010 "
            "account and debt workbooks, and compare the two modern sources against each "
            "other before either is used downstream."
        ),
        inputs=[
            "data/raw/pordata/pordata_2785_balance_by_level_1995_2025.csv",
            "data/raw/cfp/cfp_sec2010_annual_general_government_2026-04-15.xlsx",
            "data/raw/cfp/cfp_sec2010_annual_subsectors_2026-04-15.xlsx",
            "data/raw/cfp/cfp_rel_04_2026_social_security_underlying_data.xlsx",
        ],
        outputs=["Nothing. The pipeline persists these extractions; here they are inspected."],
        method="`METHODOLOGY.md` sections 3-4 and 10",
        cells=[
            (
                "md",
                """## 1. Two independent modern sources

The modern segment uses one source as the continuous balance bridge and a second,
independently parsed source for detailed components:

- **INE via PORDATA** provides the four B.9 balances for 1995-2025 and is the
  canonical modern bridge;
- **CFP ESA 2010 workbooks** provide revenue, expenditure, interest, investment,
  Maastricht debt and stock-flow adjustments, and act as a cross-check on the
  bridge.""",
            ),
            (
                "code",
                r"""from portugal_fiscal_balance.sources.cfp import (
    extract_cfp_annual,
    extract_social_security_detail,
)
from portugal_fiscal_balance.sources.pordata import load_balance_snapshot

modern = load_balance_snapshot(RAW / 'pordata' / 'pordata_2785_balance_by_level_1995_2025.csv')
cfp = extract_cfp_annual(
    RAW / 'cfp' / 'cfp_sec2010_annual_general_government_2026-04-15.xlsx',
    RAW / 'cfp' / 'cfp_sec2010_annual_subsectors_2026-04-15.xlsx',
)
ss_systems, ss_detail = extract_social_security_detail(
    RAW / 'cfp' / 'cfp_rel_04_2026_social_security_underlying_data.xlsx'
)
print('pordata balance bridge:', modern.shape)
print('cfp accounts:', cfp.accounts.shape)
print('cfp debt and stock-flow:', cfp.debt.shape)""",
            ),
            ("code", r"""display(modern.tail(8))"""),
            (
                "md",
                """## 2. Coverage of the CFP account panel

General Government components start in 1995; the three subsectors start in 2000.
That asymmetry is a property of the source and is preserved rather than filled.""",
            ),
            (
                "code",
                r"""coverage = cfp.accounts.groupby('sector')['year'].agg(['min', 'max', 'count'])
display(coverage)""",
            ),
            (
                "md",
                """## 3. Do the two modern sources agree?

The PORDATA bridge is published rounded, and the CFP workbook is a separate
compilation, so exact equality is not expected. What matters is that the
differences stay at rounding scale instead of revealing a parsing error.""",
            ),
            (
                "code",
                r"""from portugal_fiscal_balance.processing.validation import compare_modern_balance_sources

comparison = compare_modern_balance_sources(modern, cfp.general_government, cfp.subsectors)
difference_columns = [column for column in comparison.columns if column.endswith('_source_difference_m_eur')]
summary = (
    comparison[difference_columns]
    .abs()
    .max()
    .rename('max_abs_difference_m_eur')
    .to_frame()
    .round(1)
)
display(summary)
display(comparison[['year', *difference_columns]].tail(8).round(1))""",
            ),
            ("code", r"""figure = figures.modern_source_differences(comparison)"""),
            (
                "md",
                """## 4. Social Security budget tables

The CFP Social Security report is a **different accounting boundary** from the
ESA 2010 Social Security Funds sector. It is extracted here so that notebook 09
can analyse the internal Previdential / Citizenship / Special Regimes split
without merging it into the national-accounts balance.""",
            ),
            (
                "code",
                r"""display(ss_systems)
display(ss_detail.set_index('year').T)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. The PORDATA bridge is **rounded at source**. It is used for the balance panel,
   not for component-level arithmetic.
2. CFP figures for the most recent year are **provisional** in the same sense as
   the official statistics they compile.
3. Social Security budget-system tables and ESA 2010 Social Security Funds
   accounts are **never combined into one series**.""",
            ),
        ],
    ),
    Notebook(
        name="03_harmonize_and_validate.ipynb",
        title="03. Harmonisation and validation",
        purpose=(
            "Construct the canonical 1977-2025 B.9 panel, prove the subsector identity "
            "closes, quantify the 1995 vintage revision, and expose the four-year "
            "detailed-account gap instead of imputing it."
        ),
        inputs=[
            "data/raw/banco_portugal/series_longas_2023-12.xlsx",
            "data/raw/pordata/pordata_2785_balance_by_level_1995_2025.csv",
            "data/raw/cfp/cfp_sec2010_annual_general_government_2026-04-15.xlsx",
            "data/raw/cfp/cfp_sec2010_annual_subsectors_2026-04-15.xlsx",
        ],
        outputs=["Nothing. The pipeline persists the canonical panels; here they are validated."],
        method="`METHODOLOGY.md` sections 2-4",
        cells=[
            (
                "md",
                """## 1. Build the canonical balance panel

The panel takes 1977-1994 from the historical long series and 1995-2025 from the
modern bridge, attaches modern nominal GDP, and refuses to build at all unless
every year from 1977 to 2025 is present exactly once.""",
            ),
            (
                "code",
                r"""from portugal_fiscal_balance.processing.harmonize import (
    build_methodology_overlap,
    harmonize_account_panel,
    harmonize_balance_panel,
)
from portugal_fiscal_balance.processing.validation import validate_accounts, validate_balance_panel
from portugal_fiscal_balance.sources.banco_portugal import extract_long_series
from portugal_fiscal_balance.sources.cfp import extract_cfp_annual
from portugal_fiscal_balance.sources.pordata import load_balance_snapshot

historical = extract_long_series(RAW / 'banco_portugal' / 'series_longas_2023-12.xlsx')
modern = load_balance_snapshot(RAW / 'pordata' / 'pordata_2785_balance_by_level_1995_2025.csv')
cfp = extract_cfp_annual(
    RAW / 'cfp' / 'cfp_sec2010_annual_general_government_2026-04-15.xlsx',
    RAW / 'cfp' / 'cfp_sec2010_annual_subsectors_2026-04-15.xlsx',
)
panel = harmonize_balance_panel(
    historical.balances,
    modern,
    cfp.general_government[['year', 'nominal_gdp_m_eur']],
)
print(validate_balance_panel(panel))
display(panel.groupby('statistical_regime')['year'].agg(['min', 'max', 'count']))""",
            ),
            (
                "md",
                r"""## 2. Does the identity close?

$$B^{GG}_t - \left(B^{C}_t + B^{RL}_t + B^{SSF}_t\right) = 0.$$

The residual is kept as a column rather than assumed away. Published national
accounts are rounded to the million, so a tolerance of 2 M EUR is applied and
every year must fall inside it.""",
            ),
            (
                "code",
                r"""print('max |closure residual| (M EUR):', round(float(panel['closure_error_m_eur'].abs().max()), 6))
print('years inside the 2 M EUR tolerance:', int(panel['closure_within_tolerance'].sum()), 'of', len(panel))
rounding_scale = panel.loc[panel['closure_error_m_eur'].abs().ge(0.5), ['year', 'closure_error_m_eur']]
print('years with a residual of 1 M EUR or more:', len(rounding_scale))
display(rounding_scale.round(3).set_index('year').T)""",
            ),
            ("code", r"""figure = figures.closure_errors(panel)"""),
            (
                "md",
                """## 3. The 1995 splice, quantified

1995 exists in both sources. Rather than choose silently, the repository keeps
both vintages and reports the revision. The modern vintage is the one used in the
canonical panel.""",
            ),
            (
                "code",
                r"""overlap = build_methodology_overlap(historical.balances, modern)
display(overlap.round(1))""",
            ),
            ("code", r"""figure = figures.source_overlap_1995(overlap)"""),
            (
                "md",
                """The revisions are small in level terms but non-zero for every subsector, which
is exactly why no analysis in this repository fits a model across 1995. Notebook
08 detects structural breaks inside each regime separately for the same reason.

## 4. The detailed account panel and its gap

General Government components run 1977-2025 continuously. The three subsectors
have components for 1977-1995 and 2000-2025 only. The intervening four years are
absent from the sources, so they are absent here.""",
            ),
            (
                "code",
                r"""accounts = harmonize_account_panel(historical.accounts, cfp.accounts)
display(accounts.groupby(['sector', 'statistical_regime'])['year'].agg(['min', 'max', 'count']))
subsectors = accounts.loc[accounts['sector'].ne('general_government')]
print('subsector observations in 1996-1999:', int(subsectors['year'].between(1996, 1999).sum()))""",
            ),
            ("code", r"""figure = figures.account_coverage(accounts)"""),
            (
                "md",
                """## 5. Account identity check

For every sector-year with detailed components, revenue minus expenditure must
reproduce the recorded balance to numerical precision.""",
            ),
            (
                "code",
                r"""checks = validate_accounts(accounts)
worst = (
    checks.groupby('sector')['identity_error_m_eur']
    .apply(lambda column: column.abs().max())
    .rename('max_abs_identity_error_m_eur')
    .to_frame()
)
display(worst)
print('observations outside tolerance:', int((~checks['within_tolerance']).sum()))""",
            ),
            (
                "md",
                """## 6. Identity closure is not source agreement

These are two different tests and they are easy to conflate.

An **identity** check asks whether the extraction is arithmetically
self-consistent. It can close to numerical precision while both sources are wrong
in the same way, because it never consults a second source.

A **source-agreement** check asks whether two independently published sources
report the same number for the same year. Identity closure cannot establish it.

Both are collected below in one unit so they can be compared directly. The
identities close to rounding; the largest source disagreement is a Central
Government difference of roughly 67 M EUR in 2002.""",
            ),
            (
                "code",
                r"""from portugal_fiscal_balance.processing.validation import (
    compare_modern_balance_sources,
    source_validation_summary,
)
from portugal_fiscal_balance.analysis.debt import debt_reconciliation_table

comparison = compare_modern_balance_sources(modern, cfp.general_government, cfp.subsectors)
validation = source_validation_summary(
    balance_panel=panel,
    account_checks=checks,
    debt=debt_reconciliation_table(cfp.debt),
    source_comparison=comparison,
    overlap=overlap,
)
display(validation.round(3))""",
            ),
            (
                "md",
                """## 7. Which years are still provisional?

The publisher flags its most recent years as provisional and the canonical panel
carries that flag through. These are also the years the report discusses in most
detail, so the flag matters.""",
            ),
            (
                "code",
                r"""display(panel.groupby('vintage_status')['year'].agg(['min', 'max', 'count']))
print(
    'provisional years:',
    panel.loc[panel['vintage_status'].eq('provisional'), 'year'].tolist(),
)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. **Nothing is smoothed, calibrated or chained across 1995.** The panel is a
   documented splice, not a homogeneous series.
2. **1996-1999 subsector components are missing, not zero.** Any statistic that
   needs them is computed on the years that exist. The canonical B.9 panel is
   complete and is unaffected.
3. **Closure within 2 M EUR is a rounding tolerance**, not a claim that the
   sources are internally consistent to the euro.
4. **Identity closure does not imply source agreement.** Section 6 reports both,
   and neither substitutes for the other.
5. **The most recent years are provisional** and will be revised by a later
   vintage.
6. Passing these checks establishes that the extraction is faithful. It says
   nothing about whether the underlying statistics are correct.""",
            ),
        ],
    ),
    Notebook(
        name="04_balance_decomposition.ipynb",
        title="04. Long-run balance decomposition",
        purpose=(
            "Read the canonical decomposition over 1977-2025, identify the years with a "
            "positive aggregate balance, and quantify the Social Security offset metrics "
            "as accounting ratios."
        ),
        inputs=[
            "data/processed/annual_balance_metrics_1977_2025.csv",
            "outputs/metrics/analysis_summary.json",
        ],
        outputs=["Nothing. All metrics shown here are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 5",
        cells=[
            (
                "md",
                """## 1. The panel

`annual_balance_metrics_1977_2025.csv` is the canonical balance panel plus derived
offset and contribution metrics. Every column is calculated; none is transcribed.""",
            ),
            (
                "code",
                r"""annual = pd.read_csv(PROCESSED / 'annual_balance_metrics_1977_2025.csv')
levels = [
    'year',
    'general_government_balance_m_eur',
    'central_government_balance_m_eur',
    'regional_local_balance_m_eur',
    'social_security_balance_m_eur',
    'non_ssf_balance_m_eur',
    'ssf_offset_ratio',
]
print('years:', int(annual['year'].min()), 'to', int(annual['year'].max()), f'({len(annual)} observations)')
display(annual[levels].tail(12).round(3))""",
            ),
            ("code", r"""figure = figures.balances_by_subsector(annual)"""),
            (
                "md",
                """## 2. Contributions to the aggregate

The stacked columns below are the three subsector balances; their signed sum is
the General Government line. The chart is the identity drawn, so a tall column
under a shallow line means the subsectors offset one another that year.""",
            ),
            ("code", r"""figure = figures.subsector_contributions(annual)"""),
            (
                "md",
                r"""## 3. Positive aggregate-balance years

$$B^{nonSSF}_t = B^{C}_t + B^{RL}_t$$

and, when $B^{nonSSF}_t < 0$ and $B^{SSF}_t > 0$, the offset ratio is

$$O_t = \frac{B^{SSF}_t}{\left|B^{nonSSF}_t\right|}.$$

$O_t = 1$ means the positive Social Security balance is exactly the size of the
negative non-SSF balance. The ratio is an accounting comparison of two recorded
numbers. It is not a counterfactual, and it does not describe what either balance
would be under different institutional arrangements.""",
            ),
            (
                "code",
                r"""positive = annual.loc[
    annual['aggregate_balance_positive'],
    [
        'year',
        'general_government_balance_m_eur',
        'non_ssf_balance_m_eur',
        'social_security_balance_m_eur',
        'ssf_offset_ratio',
        'ssf_share_of_positive_aggregate_balance',
    ],
]
display(positive.round(3))
print('years with a positive aggregate balance:', [int(year) for year in positive['year']])""",
            ),
            ("code", r"""figure = figures.offset_ratio(annual)"""),
            (
                "md",
                """## 4. Regime-aware averages

Five-year rolling means are shown because single-year balances are volatile. The
window spans the 1995 splice for the years around it, so those values mix two
statistical vintages and should be read accordingly.""",
            ),
            (
                "code",
                r"""rolling = [
    'year',
    'general_government_balance_5y_mean_pct_gdp',
    'central_government_balance_5y_mean_pct_gdp',
    'regional_local_balance_5y_mean_pct_gdp',
    'social_security_balance_5y_mean_pct_gdp',
]
display(annual[rolling].tail(10).round(3))""",
            ),
            (
                "code",
                r"""import json

summary = json.loads((METRICS / 'analysis_summary.json').read_text(encoding='utf-8'))
latest = summary['balance_summary']['latest_year']
print('latest year in the panel:', latest['year'])
display(
    pd.Series({key: value for key, value in latest.items() if key != 'year'}, name=str(latest['year']))
    .to_frame()
    .round(3)
)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. The offset ratio is **defined only** when the non-SSF balance is negative and
   the Social Security balance is positive. It is `NaN` otherwise, by design.
2. A subsector's arithmetic contribution to a positive aggregate balance is
   **not evidence of causation** and not a statement about policy intent.
3. The 1977-1994 and 1995-2025 segments come from **different statistical
   vintages**. Long-run comparisons carry that caveat throughout.""",
            ),
        ],
    ),
    Notebook(
        name="05_revenue_expenditure.ipynb",
        title="05. Revenue and expenditure decomposition",
        purpose=(
            "Move from B.9 levels to the exact identity B = R - E, and decompose each "
            "adjacent-year balance change into a revenue change and an expenditure change."
        ),
        inputs=[
            "data/processed/subsector_accounts_1977_2025.csv",
            "outputs/tables/revenue_expenditure_change_decomposition.csv",
            "outputs/tables/largest_balance_movements.csv",
        ],
        outputs=["Nothing. All three tables are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 7",
        cells=[
            (
                "md",
                r"""## 1. Levels

For every sector-year with detailed components,

$$B_{i,t} = R_{i,t} - E_{i,t}.$$

Ratios to GDP are used for comparability across five decades of nominal growth.""",
            ),
            (
                "code",
                r"""accounts = pd.read_csv(PROCESSED / 'subsector_accounts_1977_2025.csv')
changes = pd.read_csv(TABLES / 'revenue_expenditure_change_decomposition.csv')
level_columns = [
    'year',
    'total_revenue_pct_gdp',
    'total_expenditure_pct_gdp',
    'balance_pct_gdp',
    'interest_pct_gdp',
    'gfcf_pct_gdp',
]
central = accounts.loc[accounts['sector'].eq('central_government') & accounts['year'].ge(2015), level_columns]
display(central.round(2))""",
            ),
            ("code", r"""figure = figures.revenue_expenditure(accounts, 'central_government')"""),
            (
                "md",
                """The line breaks at 1996-1999 because subsector components do not exist for those
years. The break is drawn deliberately: joining 1995 to 2000 would suggest a path
the sources do not contain.""",
            ),
            ("code", r"""figure = figures.revenue_expenditure(accounts, 'social_security_funds')"""),
            (
                "md",
                r"""## 2. Changes

Differencing the identity gives

$$\Delta B_{i,t} = \Delta R_{i,t} - \Delta E_{i,t},$$

which holds exactly for adjacent years inside a continuous source block. No
change is computed across the 1995-to-2000 subsector gap; those rows are dropped
rather than bridged.""",
            ),
            (
                "code",
                r"""ssf_changes = changes.loc[changes['sector'].eq('social_security_funds')]
display(ssf_changes.tail(10).round(1))
print('rows in the table:', len(changes))
print('year gaps present:', sorted(changes['year_gap'].dropna().unique().tolist()))""",
            ),
            (
                "code",
                r"""last_year = int(changes['year'].max())
figure = figures.revenue_expenditure_changes(
    changes, 'social_security_funds', start_year=2010, end_year=last_year
)""",
            ),
            (
                "code",
                r"""figure = figures.revenue_expenditure_changes(
    changes, 'general_government', start_year=2001, end_year=last_year
)""",
            ),
            (
                "md",
                """## 3. Which episodes were revenue-driven and which expenditure-driven?

The ranked episodes come from notebook 06, which selects them on the GDP-scaled
aggregate change within each regime. Here each is split into the revenue and
expenditure movements of **the subsector that dominates it**, not of the aggregate,
so both halves describe the same entity.

Expenditure enters the balance negatively. The contribution column is therefore minus
the expenditure change, and it is that column which adds to the revenue change to give
the subsector's balance change. The split residual is the gap between the canonical
panel's measure of that subsector change and the account panel's: two source families
that are not forced to agree.""",
            ),
            (
                "code",
                r"""movements = pd.read_csv(TABLES / 'largest_balance_movements.csv')
display(
    movements[
        [
            'regime',
            'year',
            'dominant_subsector',
            'dominant_subsector_change_m_eur',
            'dominant_revenue_change_m_eur',
            'dominant_expenditure_change_m_eur',
            'dominant_expenditure_contribution_m_eur',
            'dominant_split_error_m_eur',
        ]
    ].round(1)
)""",
            ),
            (
                "md",
                """## 4. Decomposition check

The residual is an arithmetic identity check on the persisted table, so anything
other than numerical noise would indicate a defect.""",
            ),
            (
                "code",
                r"""print('max |decomposition residual| (M EUR):', float(changes['decomposition_error_m_eur'].abs().max()))
display(
    changes.groupby('sector')['decomposition_error_m_eur']
    .apply(lambda column: column.abs().max())
    .rename('max_abs_residual_m_eur')
    .to_frame()
)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. A revenue or expenditure change is **not decomposed into policy and
   macroeconomic components**. Doing so requires assumptions this repository
   does not make.
2. Totals are used, so a change in revenue may reflect composition shifts that
   are visible only in the component columns of the account panel.
3. Changes are **never computed across a source gap**, which is why the modern
   subsector series begins contributing changes in 2001.""",
            ),
        ],
    ),
    Notebook(
        name="06_year_to_year_attribution.ipynb",
        title="06. Year-to-year balance attribution",
        purpose=(
            "Attribute every annual change in the General Government balance to changes in "
            "the three subsectors, and distinguish the level of a balance from its "
            "contribution to an annual movement."
        ),
        inputs=[
            "outputs/tables/balance_change_attribution.csv",
            "outputs/tables/largest_balance_movements.csv",
        ],
        outputs=["Nothing. Both tables are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 6",
        cells=[
            (
                "md",
                r"""## 1. An exact decomposition

$$\Delta B^{GG}_t = \Delta B^{C}_t + \Delta B^{RL}_t + \Delta B^{SSF}_t.$$

This holds by construction, so the table is a reallocation of an observed change
rather than an estimate.

The same change is also reported scaled by current-year GDP. Because the three
terms then share one denominator, the scaled version decomposes exactly as well:

$$\frac{\Delta B^{GG}_t}{GDP_t} = \frac{\Delta B^{C}_t}{GDP_t} + \frac{\Delta B^{RL}_t}{GDP_t} + \frac{\Delta B^{SSF}_t}{GDP_t}.$$

That is **not** the change in the balance ratio, which would also move with the
denominator and would not decompose additively. The scaling exists so that years
can be compared in size: ranking movements on nominal euro effectively ranks them
by how recent they are.""",
            ),
            (
                "code",
                r"""attribution = pd.read_csv(TABLES / 'balance_change_attribution.csv')
change_columns = [
    'year',
    'aggregate_change_m_eur',
    'central_change_m_eur',
    'regional_local_change_m_eur',
    'ssf_change_m_eur',
    'aggregate_change_pct_gdp',
    'change_closure_error_m_eur',
]
display(attribution[change_columns].tail(12).round(3))""",
            ),
            (
                "md",
                """## 2. Both windows, drawn separately

The attribution is plotted as two panels that stop either side of 1995. A single
panel spanning the splice would place a vintage revision among the economic
movements and give it the same visual weight. The window is written into each
title, because a stacked bar chart gives the reader no other way to tell that
years are missing from the ends.""",
            ),
            (
                "code",
                r"""figure = figures.balance_change_attribution(attribution, start_year=1996, end_year=2025)""",
            ),
            (
                "code",
                r"""figure = figures.balance_change_attribution(attribution, start_year=1978, end_year=1994)""",
            ),
            (
                "md",
                """## 3. Contribution shares

Shares are expressed against the absolute aggregate change, so a share above one
means a subsector moved further than the aggregate and was partly offset by
another subsector. A negative share means the subsector moved against the
aggregate.""",
            ),
            (
                "code",
                r"""share_columns = [
    'year',
    'aggregate_change_m_eur',
    'central_change_share_abs_aggregate_change',
    'regional_local_change_share_abs_aggregate_change',
    'ssf_change_share_abs_aggregate_change',
]
largest = attribution.reindex(attribution['aggregate_change_m_eur'].abs().sort_values(ascending=False).index)
display(largest[share_columns].head(10).round(3))""",
            ),
            (
                "md",
                """## 4. The largest movements, ranked inside each regime

Ranked on the GDP-scaled change, which removes the recency bias of a nominal
ranking, and **within** each statistical regime rather than across both. Each annual
change is computed inside one source family and is sound, but ordering historical
against modern episodes by size would compare two methodologies -- the thing this
analysis refuses to do with magnitudes everywhere else.

1995 is excluded because that change straddles the vintage splice in both panels.""",
            ),
            (
                "code",
                r"""movements = pd.read_csv(TABLES / 'largest_balance_movements.csv')
display(
    movements[
        [
            'regime',
            'rank_in_regime',
            'year',
            'direction',
            'aggregate_change_pct_gdp',
            'aggregate_change_m_eur',
            'dominant_subsector',
            'dominant_subsector_share',
        ]
    ].round(3)
)""",
            ),
            (
                "md",
                """The attribution is hierarchical: the revenue and expenditure split below is of the
subsector that dominates each move, not of the aggregate, so both halves describe the
same entity. Expenditure enters the balance negatively, so its contribution is minus
the change.""",
            ),
            (
                "code",
                r"""display(
    movements[
        [
            'regime',
            'year',
            'dominant_subsector',
            'dominant_subsector_change_m_eur',
            'dominant_revenue_change_m_eur',
            'dominant_expenditure_contribution_m_eur',
            'dominant_split_error_m_eur',
        ]
    ].round(1)
)""",
            ),
            (
                "md",
                """## 5. Closure check""",
            ),
            (
                "code",
                r"""print('max |change-identity residual| (M EUR):', round(float(attribution['change_closure_error_m_eur'].abs().max()), 6))
print('observations:', len(attribution), 'covering', int(attribution['year'].min()), 'to', int(attribution['year'].max()))""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. **Contribution is not causation.** A subsector accounting for most of an
   annual improvement has not been shown to have produced it.
2. The 1994-to-1995 change crosses the **statistical splice** and mixes a
   vintage revision with an economic movement. It is excluded from the ranked
   episodes and from both figures.
3. **The GDP-scaled change is not the change in the balance ratio.** It shares a
   denominator so the decomposition stays exact.
4. Attribution operates on **balances only**. Whether a movement came from
   revenue or expenditure is the subject of notebook 05.""",
            ),
        ],
    ),
    Notebook(
        name="07_persistence.ipynb",
        title="07. Balance persistence and sign transitions",
        purpose=(
            "Quantify how often each subsector records a positive or negative balance, how "
            "long those runs last, and what the empirical one-year sign transition "
            "frequencies are."
        ),
        inputs=[
            "outputs/tables/persistence_summary.csv",
            "outputs/tables/persistence_by_regime.csv",
            "outputs/tables/transition_probabilities.csv",
            "data/processed/fiscal_balances_1977_2025.csv",
        ],
        outputs=["Nothing. All three summaries are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 8",
        cells=[
            (
                "md",
                """## 1. Sign frequencies and run lengths

Counts are taken over the whole 1977-2025 panel. Longest runs are measured in
consecutive years with the same sign.""",
            ),
            (
                "code",
                r"""persistence = pd.read_csv(TABLES / 'persistence_summary.csv')
display(persistence.round(3))""",
            ),
            ("code", r"""figure = figures.balance_sign_states(pd.read_csv(PROCESSED / 'fiscal_balances_1977_2025.csv'))"""),
            (
                "md",
                """## 2. The pooled means describe neither regime

The magnitudes above average across the 1995 splice. The two regimes differ enough
that the pooled figure is not a good description of either one: it lands between
them and corresponds to no observed period.

Sign counts are far more robust to pooling, because a sign does not depend on the
level convention of the vintage. Both are shown per regime below so they are read
on one basis.

Runs are deliberately not recomputed per regime. A run is a property of the
uninterrupted series, and truncating it at a window boundary would report the
length of the window rather than the length of the run.""",
            ),
            (
                "code",
                r"""regime_persistence = pd.read_csv(TABLES / 'persistence_by_regime.csv')
display(regime_persistence.round(3))""",
            ),
            (
                "code",
                r"""comparison = (
    regime_persistence.pivot(index='sector', columns='regime', values='mean_balance_pct_gdp')
    .join(persistence.set_index('sector')['mean_balance_pct_gdp'].rename('pooled'))
)
display(comparison.round(3))""",
            ),
            (
                "md",
                """## 3. One-year sign transitions

Each row of the persisted table is a `state -> next_state` frequency. Pivoting
gives one transition matrix per subsector, where each row sums to one.""",
            ),
            (
                "code",
                r"""transitions = pd.read_csv(TABLES / 'transition_probabilities.csv')
matrix = transitions.pivot_table(
    index=['sector', 'state'],
    columns='next_state',
    values='probability',
    fill_value=0.0,
)
display(matrix.round(3))
display(transitions.sort_values(['sector', 'state', 'next_state']).round(3))""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. These are **empirical frequencies over 48 transitions**, not a fitted Markov
   model. No standard errors or stationarity tests are claimed.
2. A state that never occurs in the sample has **no estimated row**, which is
   why some matrices are smaller than three by three.
3. Sign persistence describes the **recorded series**. It is not a forecast and
   carries no implication about future balances.
4. Runs that span 1995 also span the **statistical splice**.
5. **Pooled magnitudes are reported for completeness only.** The regime split is
   the form in which means and medians should be read.""",
            ),
        ],
    ),
    Notebook(
        name="08_structural_breaks.ipynb",
        title="08. Structural mean shifts",
        purpose=(
            "Detect conservative piecewise-constant mean shifts separately inside the "
            "historical and the modern statistical regime, so the known 1995 splice is "
            "never a candidate economic break."
        ),
        inputs=[
            "outputs/tables/structural_breaks.csv",
            "outputs/tables/structural_break_bic_ladder.csv",
            "outputs/tables/structural_break_sensitivity.csv",
            "outputs/tables/structural_break_stability.csv",
            "data/processed/fiscal_balances_1977_2025.csv",
        ],
        outputs=["Nothing. All four break tables are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 9",
        cells=[
            (
                "md",
                """## 1. Why the model is deliberately modest

Fewer than fifty annual observations, split across two statistical regimes, do
not support a flexible change-point model. The specification is therefore:

- a piecewise-constant mean, with at most two breaks per regime;
- a minimum segment length of five years;
- exact dynamic-programming minimisation of within-segment squared error;
- BIC model selection, which may select zero breaks;
- separate estimation for 1977-1994 and 1995-2025.""",
            ),
            (
                "code",
                r"""breaks = pd.read_csv(TABLES / 'structural_breaks.csv')
display(breaks.round(3))""",
            ),
            (
                "md",
                """## 2. Fitted segments

Each chart shows one balance series with the selected segment means drawn on top
and the break years marked. A flat line across the whole regime means BIC
selected no break at all.""",
            ),
            (
                "code",
                r"""panel = pd.read_csv(PROCESSED / 'fiscal_balances_1977_2025.csv')
figure = figures.structural_break_segments(
    panel, breaks, sector='general_government', regime='1995-2025_modern'
)""",
            ),
            (
                "code",
                r"""figure = figures.structural_break_segments(
    panel, breaks, sector='social_security_funds', regime='1995-2025_modern'
)""",
            ),
            (
                "code",
                r"""figure = figures.structural_break_segments(
    panel, breaks, sector='central_government', regime='1977-1994_historical'
)""",
            ),
            (
                "md",
                """## 3. How firm are those dates?

With eighteen or thirty-one observations per regime, a single selected date should
not be read as determined. Three guards are reported.

**The BIC ladder.** Publishing only the selected break count hides how close the
alternatives were. The ladder scores every admissible count so the margin is
visible.""",
            ),
            (
                "code",
                r"""ladder = pd.read_csv(TABLES / 'structural_break_bic_ladder.csv')
display(
    ladder.pivot_table(
        index=['regime', 'sector'], columns='n_breaks', values='delta_bic_vs_best'
    ).round(2)
)""",
            ),
            (
                "md",
                """**The sensitivity grid.** Neither tuning parameter is estimated from the data,
so a date that survives only one of their values is a property of that choice
rather than of the series. Detection is re-run over all twelve combinations of a
minimum segment length in 4, 5, 6, 7 and a maximum of 1, 2 or 3 breaks.""",
            ),
            (
                "code",
                r"""sensitivity = pd.read_csv(TABLES / 'structural_break_sensitivity.csv')
print('specifications per series:', len(sensitivity) // sensitivity.groupby(['regime', 'sector']).ngroups)
display(
    sensitivity.pivot_table(
        index=['regime', 'sector'], columns=['max_breaks', 'min_segment'], values='n_breaks'
    )
)""",
            ),
            (
                "md",
                """**The stability summary.** `modal_break_years_share` is the fraction of grid
cells returning exactly the modal set of dates. It is the quantity that decides
whether a date can be stated as detected or only as a candidate.""",
            ),
            (
                "code",
                r"""stability = pd.read_csv(TABLES / 'structural_break_stability.csv')
display(stability.round(3))""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. Break dates are **candidates, not findings**. The preferred specification
   identifies shifts around the years listed; the share columns say how much of
   the specification grid agrees. This notebook attaches no historical cause to
   any of them.
2. Detection is run **within** each regime. A shift at the 1995 boundary is
   unidentifiable here by construction, which is the intent.
3. A **five-year minimum segment** means shifts near the end of the sample cannot
   be detected yet, and the sensitivity grid shows how the detected dates move
   when that length is changed.
4. Selecting a mean shift does **not** imply the underlying series is
   piecewise-constant; it is the best fit within a restricted model class.
5. **BIC differences are not tests.** A small margin means the data do not
   distinguish the alternatives, not that the selected model is rejected.""",
            ),
        ],
    ),
    Notebook(
        name="09_social_security_mechanisms.ipynb",
        title="09. Social Security Funds mechanisms",
        purpose=(
            "Analyse Social Security Funds revenue composition in national accounts, and "
            "the CFP internal budget systems separately, without merging two incompatible "
            "accounting boundaries."
        ),
        inputs=[
            "outputs/tables/social_security_account_metrics.csv",
            "outputs/tables/social_security_system_metrics_2019_2025.csv",
            "outputs/tables/social_security_detail_metrics_2024_2025.csv",
            "outputs/tables/ssf_accounting_boundary_comparison.csv",
            "outputs/tables/revenue_expenditure_change_decomposition.csv",
        ],
        outputs=["Nothing. All of these tables are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 10",
        cells=[
            (
                "md",
                """## 1. National-accounts view

This is the ESA 2010 Social Security Funds sector, the same entity that appears
in the B.9 identity. Social contributions are the dominant revenue item, and the
contribution share is the composition metric used later in the report.""",
            ),
            (
                "code",
                r"""ssf = pd.read_csv(TABLES / 'social_security_account_metrics.csv')
account_columns = [
    'year',
    'total_revenue_m_eur',
    'social_contributions_m_eur',
    'contributions_share_total_revenue',
    'total_expenditure_m_eur',
    'balance_m_eur',
]
display(ssf[account_columns].tail(12).round(3))""",
            ),
            ("code", r"""figure = figures.social_security_composition(ssf)"""),
            ("code", r"""figure = figures.social_security_contribution_share(ssf)"""),
            (
                "md",
                """## 2. A different boundary: the CFP budget systems

The CFP Social Security report decomposes the system into the Previdential
system, the Social Protection of Citizenship system and special regimes. These
are **budget-execution** aggregates. They are not a partition of the ESA 2010
Social Security Funds balance and are never added to it.""",
            ),
            (
                "code",
                r"""systems = pd.read_csv(TABLES / 'social_security_system_metrics_2019_2025.csv')
detail = pd.read_csv(TABLES / 'social_security_detail_metrics_2024_2025.csv')
display(systems.round(1))
display(detail.set_index('year').T)""",
            ),
            ("code", r"""figure = figures.social_security_systems(systems)"""),
            (
                "md",
                """Across the years the CFP publishes, the movement in the internal balances is
concentrated in the Previdential system, while the Citizenship system stays small
in both directions. That is a description of the published series, not an account
of what caused it.""",
            ),
            (
                "code",
                r"""movement = systems.set_index('year')[
    [
        'previdential_system_balance_m_eur',
        'citizenship_system_balance_m_eur',
        'special_regimes_balance_m_eur',
    ]
]
display(movement)
display((movement.iloc[-1] - movement.iloc[0]).rename('change over the published years').to_frame())""",
            ),
            (
                "md",
                """## 3. The contribution base

The decomposition above locates the movement inside the fiscal accounts. It does not
relate it to anything outside them. Contributions are levied on wages, so the natural
base is the aggregate wage bill of the economy, and the change in contributions splits
exactly into a base effect and a rate effect:

$$\Delta C_t = \tau_{t-1}\,\Delta W_t + W_{t-1}\,\Delta \tau_t + \Delta W_t\,\Delta \tau_t,
\qquad \tau_t = C_t / W_t.$$

The wage bill splits again into employees and the average wage per employee. Both
decompositions are exact; the interaction terms are carried rather than dropped.

`tau` is **not** a statutory rate. National-accounts contributions include imputed
contributions and bases other than employee wages, so it moves with coverage and
composition as well as with legislated rates.""",
            ),
            (
                "code",
                r"""base = pd.read_csv(PROCESSED / 'contribution_base_panel_1995_2025.csv')
decomposition = pd.read_csv(TABLES / 'contribution_change_decomposition.csv')
print('effective ratio, first and last:',
      round(float(base['effective_contribution_rate'].iloc[0]), 3),
      round(float(base['effective_contribution_rate'].iloc[-1]), 3))
print('max |contributions closure|:', float(decomposition['contributions_closure_error_m_eur'].abs().max()))
print('max |wage bill closure|   :', float(decomposition['wage_bill_closure_error_m_eur'].abs().max()))
display(
    decomposition[
        [
            'year',
            'contributions_change_m_eur',
            'from_wage_bill_m_eur',
            'from_effective_rate_m_eur',
            'from_employment_m_eur',
            'from_average_wage_m_eur',
        ]
    ].tail(8).round(1)
)""",
            ),
            ("code", r"""figure = figures.contribution_base_decomposition(decomposition)"""),
            (
                "md",
                """No change is computed across the 1995-to-2000 gap in subsector accounts. That is not
a formality: bridging it treats five years of wage-bill growth as one year, which moves
the regression slope below from 0.25 to 0.13 and its fit from 0.93 to 0.40 on a single
contaminated observation.""",
            ),
            (
                "code",
                r"""regression = pd.read_csv(TABLES / 'contribution_wage_bill_regression.csv')
display(regression.round(4))""",
            ),
            (
                "md",
                """## 4. Why the two boundaries must not be interchanged

This is the point the two layers exist to make. The ESA 2010 Social Security Funds
balance is the B.9 term that enters the general-government identity. The budget
systems are a different accounting object. They are close, but the difference is
non-zero in **every** overlapping year, which is exactly why a figure quoted from
the budget documents cannot be substituted for the national-accounts one.

The columns below are never added, netted or reconciled. The difference column
measures how far apart they are.""",
            ),
            (
                "code",
                r"""boundary = pd.read_csv(TABLES / 'ssf_accounting_boundary_comparison.csv')
display(boundary.round(3))
print(
    'difference range (M EUR):',
    round(float(boundary['boundary_difference_m_eur'].min()), 1),
    'to',
    round(float(boundary['boundary_difference_m_eur'].max()), 1),
)
print('years where the two are equal:', int((boundary['boundary_difference_m_eur'] == 0).sum()))""",
            ),
            ("code", r"""figure = figures.ssf_accounting_boundary(boundary)"""),
            (
                "md",
                """## 5. Contribution dynamics

The change in contributions is the revenue-side mechanism behind the national-accounts
balance. It is shown against the change in total revenue and expenditure so the
composition of each annual movement is visible.""",
            ),
            (
                "code",
                r"""changes = pd.read_csv(TABLES / 'revenue_expenditure_change_decomposition.csv')
figure = figures.revenue_expenditure_changes(
    changes, 'social_security_funds', start_year=2010, end_year=int(changes['year'].max())
)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. The two layers in this notebook have **different accounting boundaries** and
   are reported side by side, never combined. Section 3 quantifies the gap rather
   than closing it.
2. This report does **not** subtract State transfers from the Social Security
   balance and call the remainder an underlying balance. Which transfers finance
   which statutory responsibility is a legal question, not an accounting one.
3. The contribution share is a **composition ratio**. It says nothing about the
   adequacy or sustainability of the system.
4. Internal system tables cover **2019-2025 only**, with detail for 2024-2025, so
   the movement described above is a short window.
5. Attributing the movement to one system is an **accounting** statement. No
   mechanism, policy change or demographic driver is identified here.""",
            ),
        ],
    ),
    Notebook(
        name="10_intergovernmental_transfers.ipynb",
        title="10. Intergovernmental transfer sensitivity",
        purpose=(
            "Inspect a purely mechanical removal of historical net intragovernmental "
            "transfers. This is a sensitivity on where a balance is recorded, not an "
            "alternative measure of that balance."
        ),
        inputs=["outputs/tables/historical_transfer_reallocation_sensitivity.csv"],
        outputs=["Nothing. The sensitivity table is persisted by the pipeline."],
        method="`METHODOLOGY.md` section 11",
        cells=[
            (
                "md",
                r"""## 1. The mechanical operation

$$B^{sens}_{i,t} = B_{i,t} - \left(T^{received}_{i,t} - T^{paid}_{i,t}\right).$$

Historical source tables identify current and capital transfers received and paid
between public administrations, which makes this arithmetic possible for
1977-1995 only.""",
            ),
            (
                "code",
                r"""sensitivity = pd.read_csv(TABLES / 'historical_transfer_reallocation_sensitivity.csv')
sensitivity_columns = [
    'year',
    'sector',
    'intragov_received_m_eur',
    'intragov_paid_m_eur',
    'net_intragov_transfer_m_eur',
    'balance_m_eur',
    'balance_after_mechanical_transfer_removal_m_eur',
]
display(sensitivity.loc[sensitivity['year'].ge(1990), sensitivity_columns].round(1))""",
            ),
            ("code", r"""figure = figures.transfer_sensitivity(sensitivity, 'central_government')"""),
            ("code", r"""figure = figures.transfer_sensitivity(sensitivity, 'social_security_funds')"""),
            (
                "md",
                """## 2. Scale of the operation

The table below reports, by sector, how large the net transfer is relative to the
recorded balance. A large ratio means the recorded location of the balance is
sensitive to the transfer convention, and nothing more.""",
            ),
            (
                "code",
                r"""scale = sensitivity.assign(
    transfer_share_abs_balance=(
        sensitivity['net_intragov_transfer_m_eur'].abs() / sensitivity['balance_m_eur'].abs()
    )
)
display(
    scale.groupby('sector')[['net_intragov_transfer_m_eur', 'transfer_share_abs_balance']]
    .agg(['mean', 'max'])
    .round(3)
)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. This is **not a counterfactual**. A transfer usually finances an expenditure
   responsibility assigned to the recipient; removing the transfer while leaving
   the responsibility in place does not describe a coherent alternative world.
2. It is **not** an underlying or true balance, and it is never used to restate
   B.9 anywhere in this repository.
3. The calculation is available for **1977-1995 only**, because the modern source
   does not publish the same transfer breakdown.""",
            ),
        ],
    ),
    Notebook(
        name="11_primary_balance.ipynb",
        title="11. Primary balance and interest",
        purpose=(
            "Separate interest expenditure from B.9, verify the primary-balance identity "
            "against the published series, contrast headline and primary sign frequencies, "
            "and compare interest burdens across sectors."
        ),
        inputs=[
            "outputs/tables/primary_balance_and_interest.csv",
            "outputs/tables/primary_balance_sign_summary.csv",
        ],
        outputs=["Nothing. Both primary-balance tables are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 12",
        cells=[
            (
                "md",
                r"""## 1. Reconstruction and check

$$PB_{i,t} = B_{i,t} + I_{i,t}.$$

The primary balance is recomputed from the balance and interest columns and then
compared with the published primary-balance row, so the identity is verified
rather than assumed.""",
            ),
            (
                "code",
                r"""primary = pd.read_csv(TABLES / 'primary_balance_and_interest.csv')
primary_columns = [
    'year',
    'balance_m_eur',
    'interest_m_eur',
    'primary_balance_recomputed_m_eur',
    'primary_balance_identity_error_m_eur',
]
central = primary.loc[primary['sector'].eq('central_government') & primary['year'].ge(2015), primary_columns]
display(central.round(3))
print('max |identity error| (M EUR):', float(primary['primary_balance_identity_error_m_eur'].abs().max()))""",
            ),
            ("code", r"""figure = figures.primary_vs_headline(primary, 'central_government')"""),
            (
                "md",
                """## 2. The headline sign is not the primary sign

Central Government records a negative B.9 in every year of the canonical panel.
Read alone, that invites the conclusion that the subsector runs an underlying
deficit throughout. The detailed accounts do not support it.

Both statements below are descriptive and they are not in conflict: the headline
balance is negative throughout, while the primary balance, which excludes interest
by construction, is positive in a non-trivial minority of the observed years.
Interest is the arithmetic that separates them.""",
            ),
            (
                "code",
                r"""signs = pd.read_csv(TABLES / 'primary_balance_sign_summary.csv')
display(signs.round(3))""",
            ),
            (
                "code",
                r"""central_signs = signs.loc[signs['sector'].eq('central_government')].iloc[0]
print('observed years:', int(central_signs['n_years']))
print('headline balance negative in:', int(central_signs['headline_negative_years']))
print('primary balance positive in:', int(central_signs['primary_positive_years']))
print('those years:', central_signs['primary_positive_year_list'])""",
            ),
            (
                "md",
                """## 3. Interest across sectors

Interest is overwhelmingly a Central Government item, which is why the primary
and headline balances of the other subsectors nearly coincide.""",
            ),
            ("code", r"""figure = figures.interest_burden(primary)"""),
            (
                "code",
                r"""display(
    primary.groupby('sector')[['interest_pct_gdp', 'primary_balance_pct_gdp']]
    .agg(['mean', 'min', 'max'])
    .round(3)
)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. The primary balance **excludes interest by construction**. It is not a measure
   of discretionary policy and not a cyclically adjusted balance.
2. **A positive primary balance is not a sustainability result** and a negative
   headline balance is not an unsustainability result. Neither says anything about
   the debt path on its own.
3. Interest reflects the **debt stock and past financing conditions**, so a
   primary-balance comparison across decades compares different debt structures.
4. The sign counts are taken over the **detailed account panel**, so the three
   subsectors have 45 observations rather than the 49 of the canonical balance
   panel: the 1996-1999 components are missing.
5. The identity check confirms the **arithmetic**, not the appropriateness of the
   published interest series.""",
            ),
        ],
    ),
    Notebook(
        name="12_investment_diagnostic.ipynb",
        title="12. Fixed-capital-formation diagnostic",
        purpose=(
            "Quantify gross fixed capital formation relative to B.9 using an explicitly "
            "non-official diagnostic, in order to size public investment against the "
            "recorded balance."
        ),
        inputs=["outputs/tables/investment_diagnostic.csv"],
        outputs=["Nothing. The diagnostic table is persisted by the pipeline."],
        method="`METHODOLOGY.md` section 13",
        cells=[
            (
                "md",
                r"""## 1. A diagnostic, not a balance definition

$$B^{before\ GFCF}_{i,t} = B_{i,t} + GFCF_{i,t}.$$

Adding gross fixed capital formation back to B.9 answers one narrow question: how
large is public investment compared with the recorded balance? It is **not** an
official fiscal indicator, and no fiscal rule in this repository is evaluated
against it.""",
            ),
            (
                "code",
                r"""investment = pd.read_csv(TABLES / 'investment_diagnostic.csv')
diagnostic_columns = [
    'year',
    'balance_m_eur',
    'gfcf_m_eur',
    'balance_before_gfcf_m_eur',
    'gfcf_pct_gdp',
    'gfcf_share_abs_balance',
]
central = investment.loc[
    investment['sector'].eq('central_government') & investment['year'].ge(2015), diagnostic_columns
]
display(central.round(3))""",
            ),
            ("code", r"""figure = figures.investment_diagnostic(investment, 'central_government')"""),
            (
                "md",
                """## 2. Investment by sector

Regional and Local Government carries a large share of public investment relative
to its size, so the diagnostic behaves differently across subsectors.""",
            ),
            ("code", r"""figure = figures.gfcf_by_sector(investment)"""),
            (
                "code",
                r"""display(
    investment.groupby('sector')[['gfcf_pct_gdp', 'gfcf_share_abs_balance']]
    .agg(['mean', 'median', 'max'])
    .round(3)
)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. The balance before GFCF is **not** a golden-rule balance, a structural
   balance, or any published indicator.
2. GFCF is **gross**: no consumption of fixed capital is netted off, so the
   diagnostic overstates the change in the public capital stock.
3. Investment is **lumpy**. Single-year ratios can be dominated by one project or
   one reclassification.""",
            ),
        ],
    ),
    Notebook(
        name="13_debt_reconciliation.ipynb",
        title="13. Debt and stock-flow reconciliation",
        purpose=(
            "Reconcile modern Maastricht debt changes with B.9 and the stock-flow "
            "adjustment, showing that debt dynamics are not the mirror image of the annual "
            "balance."
        ),
        inputs=["outputs/tables/debt_stock_flow_reconciliation.csv"],
        outputs=["Nothing. The reconciliation table is persisted by the pipeline."],
        method="`METHODOLOGY.md` section 14",
        cells=[
            (
                "md",
                r"""## 1. The reconciliation

$$\Delta Debt_t = -B_t + SFA_t.$$

The stock-flow adjustment absorbs everything that changes debt without passing
through the annual balance: financial-asset transactions, valuation effects,
timing differences and statistical adjustments. It is computed here as a residual
check on the persisted table.""",
            ),
            (
                "code",
                r"""debt = pd.read_csv(TABLES / 'debt_stock_flow_reconciliation.csv')
debt_columns = [
    'year',
    'balance_m_eur',
    'debt_change_m_eur',
    'stock_flow_adjustment_m_eur',
    'debt_pct_gdp',
    'stock_flow_adjustment_pct_gdp',
    'reconciliation_error_m_eur',
]
general = debt.loc[debt['sector'].eq('general_government') & debt['year'].ge(2010), debt_columns]
display(general.round(3))
print('max |reconciliation residual| (M EUR):', float(debt['reconciliation_error_m_eur'].abs().max()))""",
            ),
            ("code", r"""figure = figures.debt_and_stock_flow(debt)"""),
            (
                "md",
                """## 2. What moves the debt ratio

The columns below split each annual debt change into minus the balance and the
stock-flow adjustment. In several years the adjustment is the larger term, which
is the point of running the reconciliation at all.""",
            ),
            ("code", r"""figure = figures.debt_change_decomposition(debt)"""),
            (
                "code",
                r"""general_government = debt.loc[debt['sector'].eq('general_government')].copy()
general_government['sfa_share_abs_debt_change'] = (
    general_government['stock_flow_adjustment_m_eur'].abs()
    / general_government['debt_change_m_eur'].abs()
)
display(
    general_government.loc[
        general_government['sfa_share_abs_debt_change'].gt(1.0),
        ['year', 'balance_m_eur', 'debt_change_m_eur', 'stock_flow_adjustment_m_eur'],
    ].round(1)
)""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. The stock-flow adjustment is a **residual category**, not a behavioural
   variable. A large value is a signal to consult the source documentation, not
   an anomaly by itself.
2. Reconciliation is available for the **modern regime only**, where debt and
   adjustment series are published on a consistent basis.
3. The debt ratio changes with **nominal GDP** as well as with debt, so a falling
   ratio does not imply falling debt.""",
            ),
        ],
    ),
    Notebook(
        name="14_macroeconomic_comovement.ipynb",
        title="14. Descriptive macroeconomic co-movement",
        purpose=(
            "Estimate transparent HAC regressions of balance ratios on nominal GDP growth "
            "for the full period, plus a small historical labour-market specification, and "
            "state plainly what these estimates are not."
        ),
        inputs=[
            "outputs/tables/nominal_gdp_balance_comovement.csv",
            "outputs/tables/historical_ssf_labour_comovement.csv",
            "data/processed/macro_panel_1977_2025.csv",
        ],
        outputs=["Nothing. Both regression tables are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 15",
        cells=[
            (
                "md",
                r"""## 1. Full-period specification

For each subsector,

$$B_{i,t}/GDP_t = \alpha_i + \beta_i g^{nominal}_t + \gamma_i I(t \ge 1995) + \epsilon_{i,t},$$

with HAC standard errors. Nominal GDP growth is used because it is the one
macroeconomic variable reconstructible on a consistent basis from the bundled
sources across the whole 1977-2025 span. The regime dummy absorbs the level
difference between the two statistical vintages; it is not an economic effect.""",
            ),
            (
                "code",
                r"""nominal = pd.read_csv(TABLES / 'nominal_gdp_balance_comovement.csv')
display(nominal.round(4))""",
            ),
            ("code", r"""macro = pd.read_csv(PROCESSED / 'macro_panel_1977_2025.csv')
figure = figures.nominal_growth_scatter(macro, sector='general_government')"""),
            ("code", r"""figure = figures.nominal_growth_scatter(macro, sector='social_security_funds')"""),
            (
                "md",
                """The scatter plots show why the coefficient should be read as co-movement only:
the two regimes occupy different regions of the growth axis, because the
historical period combines high inflation with high nominal growth.""",
            ),
            (
                "md",
                """## 2. Historical labour-market specification

For 1978-1995 the historical workbook also supports a small Social Security
specification using employment growth and the unemployment rate.""",
            ),
            (
                "code",
                r"""labour = pd.read_csv(TABLES / 'historical_ssf_labour_comovement.csv')
display(labour.T.rename(columns={0: 'estimate'}).round(4))""",
            ),
            ("code", r"""figure = figures.historical_labour_context(macro)"""),
            (
                "md",
                f"""{LIMITS_HEADING}

1. **Nominal GDP growth is not an output gap.** Nothing here is a cyclically
   adjusted or structural balance.
2. These are **descriptive co-movement estimates**, not causal effects. No
   identification strategy is claimed and none is implied.
3. The sample is **short and serially correlated**. HAC standard errors address
   the inference arithmetic, not the small-sample or specification risk.
4. The regime dummy is a **statistical control for the 1995 splice**, not an
   estimate of a policy change.
5. The labour specification covers **18 observations**. It is reported for
   transparency and should not carry analytical weight on its own.""",
            ),
        ],
    ),
    Notebook(
        name="15_european_benchmark.ipynb",
        title="15. European benchmark",
        purpose=(
            "Place Portugal's subsector composition in the distribution of European "
            "reporters, which is the one question a single-country study cannot answer."
        ),
        inputs=[
            "data/processed/european_subsector_panel_1995_2025.csv",
            "outputs/tables/european_benchmark_summary.csv",
            "outputs/tables/european_benchmark_position.csv",
        ],
        outputs=["Nothing. All three artefacts are persisted by the pipeline."],
        method="`METHODOLOGY.md` section 17",
        cells=[
            (
                "md",
                r"""## 1. Why leave Portugal at all

Every other notebook describes one country. That establishes how Portugal behaves and
cannot establish whether it is unusual, because there is no comparison set. ESA 2010
requires the same subsector breakdown from every reporter, so the comparison exists.

Three construction choices decide whether the comparison is fair.

**The non-Social-Security aggregate includes state government.**

$$B^{nonSSF}_{c,t} = B^{S.1311}_{c,t} + B^{S.1312}_{c,t} + B^{S.1313}_{c,t}.$$

Portugal has no S.1312 tier; Germany, Spain, Austria, Belgium and Switzerland do.
Omitting it would leave their identity open and understate their non-Social-Security
deficits. A missing tier contributes zero because it does not exist, not because a
value is unknown.

**Ratios use national currency.** Eurostat publishes shares of GDP to one decimal,
which is an unusable denominator: a balance printed as -0.2 could sit anywhere in a
band wide enough to move the offset ratio by a quarter of its value.

**Coverage is made comparable.** A country-year needs all four required sectors, and a
reporter needs at least fifteen complete years before its frequencies are compared with
a reporter covering thirty.""",
            ),
            (
                "code",
                r"""panel = pd.read_csv(PROCESSED / 'european_subsector_panel_1995_2025.csv')
summary = pd.read_csv(TABLES / 'european_benchmark_summary.csv')
print('country-years:', len(panel), 'of which complete:', int(panel['complete'].sum()))
print('reporters in the summary:', len(summary))
print('offset ratio defined in:', int(panel['offset_ratio'].notna().sum()), 'country-years')
print('max |identity residual|, national currency:', round(float(panel['closure_error_mio_nac'].abs().max()), 2))""",
            ),
            (
                "md",
                """## 2. Does the external source agree with our own panel?

Eurostat compiles the Portuguese figures independently of the PORDATA bridge this
repository uses. Agreement is therefore a check on the extraction, not a tautology.""",
            ),
            (
                "code",
                r"""domestic = pd.read_csv(PROCESSED / 'fiscal_balances_1977_2025.csv')
check = (
    panel.loc[panel['country'].eq('PT'), ['year', 'general_government_mio_nac', 'social_security_mio_nac']]
    .merge(
        domestic[['year', 'general_government_balance_m_eur', 'social_security_balance_m_eur']],
        on='year',
    )
)
check['gg_gap'] = check['general_government_mio_nac'] - check['general_government_balance_m_eur']
check['ssf_gap'] = check['social_security_mio_nac'] - check['social_security_balance_m_eur']
print('years compared:', len(check))
print('max |General Government gap| (M EUR):', round(float(check['gg_gap'].abs().max()), 2))
print('max |Social Security gap| (M EUR):', round(float(check['ssf_gap'].abs().max()), 2))
display(check.tail(4).round(2))""",
            ),
            (
                "md",
                """## 3. Sign frequencies across reporters

Ordered by the frequency of a Social Security surplus, because the position in the
ranking is the quantity of interest.""",
            ),
            (
                "code",
                r"""display(
    summary.sort_values('share_ssf_positive', ascending=False)[
        [
            'country',
            'n_years',
            'share_central_negative',
            'share_ssf_positive',
            'mean_ssf_pct_gdp',
            'median_offset_ratio',
        ]
    ].round(3)
)""",
            ),
            ("code", r"""figure = figures.european_benchmark(summary)"""),
            ("code", r"""figure = figures.european_offset_distribution(panel)"""),
            (
                "md",
                """## 4. Where Portugal sits

The answer is not uniform, which is the substantive result. A persistently
deficit-running central tier is common in Europe. A Social Security surplus of
Portugal's frequency and size is not.""",
            ),
            (
                "code",
                r"""position = pd.read_csv(TABLES / 'european_benchmark_position.csv')
display(position.round(3))
central_always = summary.loc[summary['share_central_negative'].ge(1.0), 'country'].tolist()
print('reporters with a Central Government deficit in every year:', len(central_always))
print(' ', central_always)""",
            ),
            (
                "md",
                """## 5. The composition of a surplus year

This is the paper's headline composition restated as a cross-country question: when a
country records an aggregate surplus, is its non-Social-Security balance in deficit?""",
            ),
            (
                "code",
                r"""with_surplus = summary.loc[summary['n_aggregate_positive'].gt(0)].copy()
with_surplus['share_offsetting'] = (
    with_surplus['n_aggregate_positive_with_negative_non_ssf'] / with_surplus['n_aggregate_positive']
)
display(
    with_surplus.sort_values('share_offsetting', ascending=False)[
        ['country', 'n_aggregate_positive', 'n_aggregate_positive_with_negative_non_ssf', 'share_offsetting']
    ].round(3)
)
total = int(with_surplus['n_aggregate_positive'].sum())
offsetting = int(with_surplus['n_aggregate_positive_with_negative_non_ssf'].sum())
print(f'surplus country-years: {offsetting} of {total} have a negative non-SSF balance ({100 * offsetting / total:.0f}%)')
print('reporters showing it in every surplus year:', int((with_surplus['share_offsetting'] >= 1.0).sum()))""",
            ),
            (
                "md",
                f"""{LIMITS_HEADING}

1. **This is a distribution, not a test.** Locating Portugal in a spread of accounting
   compositions says how common that composition is. It says nothing about why any
   country's composition takes the form it does.
2. **Nothing is held constant.** Reporters differ in whether they operate a state tier,
   in how contributory schemes are assigned between tiers, in pension-system maturity
   and in how transfers are routed between subsectors.
3. **Portugal's surplus years are few.** A share computed over four observations is
   reported with its count beside it and should not be read as a rate.
4. **Eurostat vintages differ from the domestic sources.** The agreement checked in
   section 2 is to rounding, not to the euro.
5. Excluding reporters with fewer than fifteen complete years is a **stated choice**,
   not a property of the data; the excluded reporters remain in the persisted panel.""",
            ),
        ],
    ),
    Notebook(
        name="16_build_report.ipynb",
        title="16. Build the final report",
        purpose=(
            "Regenerate the English LaTeX report strictly from persisted pipeline outputs, "
            "and show which files the renderer consumes so that every reported number is "
            "traceable to a CSV or JSON artefact."
        ),
        inputs=[
            "outputs/tables/*.csv",
            "outputs/metrics/analysis_summary.json",
            "data/processed/*.csv",
        ],
        outputs=["`report/report.tex`"],
        method="`METHODOLOGY.md` section 16",
        plots=False,
        cells=[
            (
                "md",
                """## 1. Render

The renderer reads persisted outputs and writes LaTeX. It contains no analysis:
if a number is in the report, it is in a CSV or JSON file first. That is what
makes the report checkable without running any code.""",
            ),
            (
                "code",
                r"""from portugal_fiscal_balance.reporting.render import render_report

report_path = render_report(ROOT)
text = report_path.read_text(encoding='utf-8')
print('written:', report_path.relative_to(ROOT).as_posix())
print('size:', f'{len(text) / 1024:.1f} kB')
print('lines:', len(text.splitlines()))""",
            ),
            (
                "md",
                """## 2. Inputs the report consumes""",
            ),
            (
                "code",
                r"""consumed = pd.DataFrame(
    [
        {
            'artefact': str(path.relative_to(ROOT)).replace('\\', '/'),
            'size_kb': round(path.stat().st_size / 1024, 1),
        }
        for path in [
            *sorted((ROOT / 'outputs' / 'tables').glob('*.csv')),
            *sorted((ROOT / 'outputs' / 'metrics').glob('*.json')),
        ]
    ]
)
display(consumed)""",
            ),
            (
                "md",
                """## 3. Structure of the generated report""",
            ),
            (
                "code",
                r"""sections = [line.strip() for line in text.splitlines() if line.startswith('\\section')]
print(len(sections), 'sections')
for line in sections:
    print(' -', line.removeprefix('\\section{').removesuffix('}'))""",
            ),
            (
                "code",
                r"""figure_lines = [line.strip() for line in text.splitlines() if 'includegraphics' in line]
print(len(figure_lines), 'figures included from outputs/figures')
for line in figure_lines:
    print(' -', line.split('{')[-1].removesuffix('}'))""",
            ),
            (
                "md",
                """## 4. First page of the source""",
            ),
            ("code", r"""print(text[:2500])"""),
            (
                "md",
                f"""{LIMITS_HEADING}

1. The report **restates persisted results**. It introduces no new calculation
   and no conclusion that is not supported by an artefact in `outputs/`.
2. It carries the **same caveats** as the notebooks: the 1995 splice, the
   1996-1999 component gap, and the descriptive nature of every regression.
3. Regenerating the report without first running the pipeline reproduces the
   **previous** outputs, because the renderer reads files rather than recomputing
   them.""",
            ),
        ],
    ),
]


def main() -> None:
    """Write every notebook narrative to the notebooks directory."""
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)
    for index, spec in enumerate(SPECS):
        notebook = build(spec, index, SPECS)
        nbf.write(notebook, NOTEBOOKS / spec.name)
        print(f"wrote {spec.name} ({len(notebook.cells)} cells)")
    print(f"Created {len(SPECS)} notebooks in {NOTEBOOKS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

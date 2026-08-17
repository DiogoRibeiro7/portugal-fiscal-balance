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
                f"""{LIMITS_HEADING}

1. **Nothing is smoothed, calibrated or chained across 1995.** The panel is a
   documented splice, not a homogeneous series.
2. **1996-1999 subsector components are missing, not zero.** Any statistic that
   needs them is computed on the years that exist.
3. **Closure within 2 M EUR is a rounding tolerance**, not a claim that the
   sources are internally consistent to the euro.
4. Passing these checks establishes that the extraction is faithful. It says
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
display(pd.Series(summary['balance_summary']['latest_2025'], name='2025').to_frame().round(3))""",
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
        ],
        outputs=["Nothing. Both tables are persisted by the pipeline."],
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
                r"""figure = figures.revenue_expenditure_changes(changes, 'social_security_funds', start_year=2010)""",
            ),
            (
                "md",
                """## 3. Decomposition check

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
        inputs=["outputs/tables/balance_change_attribution.csv"],
        outputs=["Nothing. The attribution table is persisted by the pipeline."],
        method="`METHODOLOGY.md` section 6",
        cells=[
            (
                "md",
                r"""## 1. An exact decomposition

$$\Delta B^{GG}_t = \Delta B^{C}_t + \Delta B^{RL}_t + \Delta B^{SSF}_t.$$

This holds by construction, so the table is a reallocation of an observed change
rather than an estimate.""",
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
    'change_closure_error_m_eur',
]
display(attribution[change_columns].tail(12).round(1))""",
            ),
            ("code", r"""figure = figures.balance_change_attribution(attribution)"""),
            (
                "md",
                """## 2. The largest annual movements

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
                """## 3. Closure check""",
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
   vintage revision with an economic movement.
3. Attribution operates on **balances only**. Whether a movement came from
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
            "outputs/tables/transition_probabilities.csv",
            "data/processed/fiscal_balances_1977_2025.csv",
        ],
        outputs=["Nothing. Both summaries are persisted by the pipeline."],
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
                """## 2. One-year sign transitions

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
4. Runs that span 1995 also span the **statistical splice**.""",
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
            "data/processed/fiscal_balances_1977_2025.csv",
        ],
        outputs=["Nothing. The break table is persisted by the pipeline."],
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
                f"""{LIMITS_HEADING}

1. Break dates are **statistical summaries**. This notebook attaches no
   historical cause to any of them.
2. Detection is run **within** each regime. A shift at the 1995 boundary is
   unidentifiable here by construction, which is the intent.
3. A **five-year minimum segment** means shifts near the end of the sample cannot
   be detected yet.
4. Selecting a mean shift does **not** imply the underlying series is
   piecewise-constant; it is the best fit within a restricted model class.""",
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
        ],
        outputs=["Nothing. All three tables are persisted by the pipeline."],
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
                f"""{LIMITS_HEADING}

1. The two layers in this notebook have **different accounting boundaries** and
   are reported side by side, never combined.
2. The repository does **not** subtract State transfers from the Social Security
   balance and call the remainder an underlying balance. Which transfers finance
   which statutory responsibility is a legal question, not an accounting one.
3. The contribution share is a **composition ratio**. It says nothing about the
   adequacy or sustainability of the system.
4. Internal system tables cover **2019-2025 only**, with detail for 2024-2025.""",
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
            "against the published series, and compare interest burdens across sectors."
        ),
        inputs=["outputs/tables/primary_balance_and_interest.csv"],
        outputs=["Nothing. The primary-balance table is persisted by the pipeline."],
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
                """## 2. Interest across sectors

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
2. Interest reflects the **debt stock and past financing conditions**, so a
   primary-balance comparison across decades compares different debt structures.
3. The identity check confirms the **arithmetic**, not the appropriateness of the
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
        name="15_build_report.ipynb",
        title="15. Build the final report",
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
print('written:', report_path.relative_to(ROOT))
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

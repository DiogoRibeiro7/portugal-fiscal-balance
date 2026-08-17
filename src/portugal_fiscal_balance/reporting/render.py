"""Render the final English LaTeX report from persisted CSV/JSON outputs.

The renderer performs no analysis. Every number it prints is read from a file
that the pipeline already wrote, which is what makes the report checkable
without running any code: each section states which artefact it draws on, and
the appendix maps every section to its notebook and its persisted table.

Nothing here is pinned to a particular final year. The latest year is taken from
each artefact separately, because the sources end at different dates: the
balance panel runs to 2025 while, for example, the Social Security budget detail
covers two years only.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml

from portugal_fiscal_balance.reporting import latex
from portugal_fiscal_balance.schemas import SECTOR_LABELS

TITLE = "Portugal's General-Government Balance by Subsector, 1977--2025"
AUTHOR = "Diogo Ribeiro"
SUBJECT = (
    "Accounting decomposition of Portugal's general-government net lending "
    "and net borrowing by subsector"
)

#: Sections of the report, the notebook that produces them and the artefact they read.
ARTEFACT_INDEX: tuple[tuple[str, str, str], ...] = (
    ("Data, sources and validation", "03_harmonize_and_validate", "data/processed/fiscal_balances_1977_2025.csv"),
    ("Long-run subsector decomposition", "04_balance_decomposition", "data/processed/annual_balance_metrics_1977_2025.csv"),
    ("Year-to-year attribution", "06_year_to_year_attribution", "outputs/tables/balance_change_attribution.csv"),
    ("Revenue and expenditure dynamics", "05_revenue_expenditure", "outputs/tables/revenue_expenditure_change_decomposition.csv"),
    ("Social Security Funds", "09_social_security_mechanisms", "outputs/tables/social_security_account_metrics.csv"),
    ("Primary balance and interest", "11_primary_balance", "outputs/tables/primary_balance_and_interest.csv"),
    ("Fixed-capital-formation diagnostic", "12_investment_diagnostic", "outputs/tables/investment_diagnostic.csv"),
    ("Debt and stock-flow adjustment", "13_debt_reconciliation", "outputs/tables/debt_stock_flow_reconciliation.csv"),
    ("Persistence and structural mean shifts", "07_persistence, 08_structural_breaks", "outputs/tables/persistence_summary.csv"),
    ("Descriptive macroeconomic co-movement", "14_macroeconomic_comovement", "outputs/tables/nominal_gdp_balance_comovement.csv"),
    ("Intergovernmental transfers", "10_intergovernmental_transfers", "outputs/tables/historical_transfer_reallocation_sensitivity.csv"),
)


@dataclass(frozen=True)
class ReportInputs:
    """Every persisted artefact the report reads, loaded once."""

    root: Path
    version: str
    summary: dict[str, Any]
    sources: pd.DataFrame
    annual: pd.DataFrame
    accounts: pd.DataFrame
    overlap: pd.DataFrame
    attribution: pd.DataFrame
    revenue_expenditure: pd.DataFrame
    recent: pd.DataFrame
    persistence: pd.DataFrame
    transitions: pd.DataFrame
    breaks: pd.DataFrame
    ssf: pd.DataFrame
    ss_systems: pd.DataFrame
    ss_detail: pd.DataFrame
    primary: pd.DataFrame
    investment: pd.DataFrame
    debt: pd.DataFrame
    nominal_comovement: pd.DataFrame
    labour_comovement: pd.DataFrame


def _read_version(root: Path) -> str:
    """Read the repository version, so an archived report identifies its build."""
    content = (root / "pyproject.toml").read_bytes()
    return str(tomllib.loads(content.decode("utf-8"))["project"]["version"])


#: Acronyms that title-casing a configuration key would otherwise mangle.
_ACRONYMS: dict[str, str] = {"Cfp": "CFP", "Ine": "INE", "Pordata": "PORDATA", "Sec2010": "ESA 2010"}


def _source_label(key: str) -> str:
    """Turn a `config/sources.yml` key into a readable table label."""
    label = key.replace("_", " ").title()
    for wrong, right in _ACRONYMS.items():
        label = label.replace(wrong, right)
    return label


def _read_sources(root: Path) -> pd.DataFrame:
    """Build the source provenance table from the pinned configuration and hashes."""
    config = cast(
        dict[str, dict[str, dict[str, str]]],
        yaml.safe_load((root / "config" / "sources.yml").read_text(encoding="utf-8")),
    )
    hashes = cast(
        dict[str, str],
        json.loads((root / "outputs" / "metrics" / "raw_file_sha256.json").read_text(encoding="utf-8")),
    )
    records = [
        {
            "Source": _source_label(key),
            "Institution": entry["institution"],
            "Coverage used": entry["coverage"],
            "SHA-256 prefix": hashes.get(entry["local_file"], "")[:12],
        }
        for key, entry in config["sources"].items()
    ]
    return pd.DataFrame.from_records(records)


def load(root: Path) -> ReportInputs:
    """Load every artefact the report needs from the persisted outputs."""
    processed = root / "data" / "processed"
    interim = root / "data" / "interim"
    tables = root / "outputs" / "tables"
    metrics = root / "outputs" / "metrics"
    return ReportInputs(
        root=root,
        version=_read_version(root),
        summary=cast(
            dict[str, Any],
            json.loads((metrics / "analysis_summary.json").read_text(encoding="utf-8")),
        ),
        sources=_read_sources(root),
        annual=pd.read_csv(processed / "annual_balance_metrics_1977_2025.csv"),
        accounts=pd.read_csv(processed / "subsector_accounts_1977_2025.csv"),
        overlap=pd.read_csv(interim / "methodology_overlap_1995.csv"),
        attribution=pd.read_csv(tables / "balance_change_attribution.csv"),
        revenue_expenditure=pd.read_csv(tables / "revenue_expenditure_change_decomposition.csv"),
        recent=pd.read_csv(tables / "recent_balance_decomposition_2010_2025.csv"),
        persistence=pd.read_csv(tables / "persistence_summary.csv"),
        transitions=pd.read_csv(tables / "transition_probabilities.csv"),
        breaks=pd.read_csv(tables / "structural_breaks.csv"),
        ssf=pd.read_csv(tables / "social_security_account_metrics.csv"),
        ss_systems=pd.read_csv(tables / "social_security_system_metrics_2019_2025.csv"),
        ss_detail=pd.read_csv(tables / "social_security_detail_metrics_2024_2025.csv"),
        primary=pd.read_csv(tables / "primary_balance_and_interest.csv"),
        investment=pd.read_csv(tables / "investment_diagnostic.csv"),
        debt=pd.read_csv(tables / "debt_stock_flow_reconciliation.csv"),
        nominal_comovement=pd.read_csv(tables / "nominal_gdp_balance_comovement.csv"),
        labour_comovement=pd.read_csv(tables / "historical_ssf_labour_comovement.csv"),
    )


def _view(frame: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    """Select columns in a fixed order and replace them with presentation labels."""
    return frame[list(columns)].rename(columns=columns)


def _label_sectors(frame: pd.DataFrame, *, column: str = "sector") -> pd.DataFrame:
    """Order sectors canonically and replace the codes with readable labels."""
    ordered = frame.copy()
    ordered[column] = pd.Categorical(
        ordered[column], categories=list(SECTOR_LABELS), ordered=True
    )
    ordered = ordered.sort_values([column, "year"] if "year" in ordered.columns else [column])
    ordered[column] = ordered[column].map(SECTOR_LABELS).astype("string")
    return ordered


def _latest(frame: pd.DataFrame, **filters: str) -> pd.Series[Any]:
    """Return the most recent row of a frame, after optional equality filters."""
    subset = frame
    for column, value in filters.items():
        subset = subset.loc[subset[column].eq(value)]
    return cast("pd.Series[Any]", subset.loc[subset["year"].idxmax()])


def _tail_years(frame: pd.DataFrame, count: int, **filters: str) -> pd.DataFrame:
    """Return the last ``count`` years of a frame, after optional equality filters."""
    subset = frame
    for column, value in filters.items():
        subset = subset.loc[subset[column].eq(value)]
    return subset.sort_values("year").tail(count)


def _year_list(years: list[int]) -> str:
    """Render a short list of years as running prose."""
    if len(years) == 1:
        return str(years[0])
    return ", ".join(str(year) for year in years[:-1]) + f" and {years[-1]}"


def _abstract(data: ReportInputs) -> str:
    """Build the abstract and the reading guide."""
    validation = data.summary["balance_validation"]
    positive = [int(year) for year in data.summary["balance_summary"]["positive_aggregate_balance_years"]]
    return rf"""\begin{{abstract}}
\noindent
This report decomposes Portugal's annual general-government net lending (+) / net
borrowing (-) into Central Government, Regional and Local Government, and Social
Security Funds (SSF), for the {validation['n_years']} years from
{int(data.annual['year'].min())} to {int(data.annual['year'].max())}. The analysis is
empirical and accounting-focused. It covers long-run balance composition, exact
year-to-year attribution, revenue and expenditure dynamics, sign persistence,
conservative structural mean shifts, Social Security revenue composition and internal
systems, primary balances and interest, public investment, debt-flow reconciliation,
and descriptive macroeconomic co-movement.

\noindent
The central accounting identity is
\[
B^{{GG}}_t = B^{{C}}_t + B^{{RL}}_t + B^{{SSF}}_t,
\]
and it closes for every year in the panel to within rounding. The aggregate balance is
positive in {len(positive)} of {validation['n_years']} years: {_year_list(positive)}.

\noindent
No causal, normative, or policy-intent interpretation is assigned to any result. Every
figure and table in this report is generated from a persisted artefact listed in
Appendix~\ref{{sec:artefacts}}; no value is transcribed by hand.
\end{{abstract}}

\tableofcontents
"""


def _section_glance(data: ReportInputs) -> str:
    """Build the results-at-a-glance section."""
    latest = _latest(data.annual)
    year = int(latest["year"])
    validation = data.summary["balance_validation"]
    positive = [int(value) for value in data.summary["balance_summary"]["positive_aggregate_balance_years"]]
    glance = pd.DataFrame.from_records(
        [
            {"Quantity": "Panel coverage", "Value": f"{int(data.annual['year'].min())}--{year}"},
            {"Quantity": "Annual observations", "Value": f"{validation['n_years']}"},
            {"Quantity": "Sector-year detailed account observations", "Value": f"{data.summary['n_account_observations']}"},
            {"Quantity": "Years with a positive aggregate balance", "Value": f"{len(positive)}"},
            {
                "Quantity": f"General Government balance, {year}",
                "Value": f"{latest['general_government_balance_m_eur']:,.0f} M EUR "
                f"({latest['general_government_balance_pct_gdp']:.2f}% GDP)",
            },
            {
                "Quantity": f"Combined non-SSF balance, {year}",
                "Value": f"{latest['non_ssf_balance_m_eur']:,.0f} M EUR "
                f"({latest['non_ssf_balance_pct_gdp']:.2f}% GDP)",
            },
            {
                "Quantity": f"Social Security Funds balance, {year}",
                "Value": f"{latest['social_security_balance_m_eur']:,.0f} M EUR "
                f"({latest['social_security_balance_pct_gdp']:.2f}% GDP)",
            },
            {
                "Quantity": "Maximum absolute subsector closure residual",
                "Value": f"{validation['max_abs_closure_error_m_eur']:.2f} M EUR",
            },
            {
                "Quantity": "Maximum absolute account identity error",
                "Value": f"{data.summary['max_abs_account_identity_error_m_eur']:.2e} M EUR",
            },
            {
                "Quantity": "Maximum absolute debt reconciliation residual",
                "Value": f"{data.summary['max_abs_debt_reconciliation_error_m_eur']:.2e} M EUR",
            },
            {
                "Quantity": "Subsector account years left un-imputed",
                "Value": f"{data.summary['n_subsector_account_gap_years_1996_1999']} (1996--1999)",
            },
        ]
    )
    body = latex.table(
        glance,
        caption="Headline quantities, each read from a persisted artefact.",
        label="glance",
        note="Residual quantities are validation checks on the extraction and the "
        "accounting identities, not economic results.",
    )
    return rf"""\section{{Results at a Glance}}
\label{{sec:glance}}

{body}
The three residual rows are the report's own audit trail. The subsector identity closes
to within the one-million-euro rounding of the published sources; revenue minus
expenditure reproduces the recorded balance to numerical precision; and the modern debt
change reconciles exactly with the balance and the stock-flow adjustment. A change in
any of those rows would indicate a defect in extraction rather than a finding.
"""


def _section_data(data: ReportInputs) -> str:
    """Build the data, sources and validation section."""
    coverage_source = data.accounts.groupby("sector")["year"].agg(["min", "max", "count"]).reset_index()
    coverage_source["missing"] = (
        coverage_source["max"] - coverage_source["min"] + 1 - coverage_source["count"]
    )
    coverage = _view(
        _label_sectors(coverage_source),
        {
            "sector": "Sector",
            "min": "First year",
            "max": "Last year",
            "count": "Observations",
            "missing": "Years absent",
        },
    )
    overlap = _view(
        data.overlap.assign(metric=data.overlap["metric"].map(_METRIC_LABELS)),
        {
            "metric": "Balance",
            "historical_1995_m_eur": "Historical vintage (M EUR)",
            "modern_1995_m_eur": "Modern vintage (M EUR)",
            "difference_m_eur": "Revision (M EUR)",
        },
    )
    sources_table = latex.table(
        data.sources,
        caption="Bundled sources, the coverage used from each, and the first twelve "
        "hexadecimal digits of the SHA-256 digest of the retained file.",
        label="sources",
        note="Download URLs and local paths are recorded in \\path{config/sources.yml}; "
        "full digests for every bundled file are in "
        "\\path{outputs/metrics/raw_file_sha256.json}.",
    )
    coverage_table = latex.table(
        coverage,
        caption="Coverage of the detailed account panel. The absent years are the "
        "1996--1999 subsector components, which are missing from both sources and are "
        "not imputed.",
        label="coverage",
        digits=0,
    )
    overlap_table = latex.table(
        overlap,
        caption="The 1995 overlap. Both vintages are retained; the canonical panel uses "
        "the modern one.",
        label="overlap",
    )
    coverage_figure = latex.figure(
        "10_account_coverage.png",
        caption="Detailed account coverage by sector and statistical regime.",
        label="coverage",
    )
    return rf"""\section{{Data, Sources and Validation}}
\label{{sec:data}}

The canonical balance panel takes 1977--1994 from the Banco de Portugal / INE historical
long series and 1995--{int(data.annual['year'].max())} from INE data distributed through
PORDATA. The CFP ESA 2010 workbooks supply modern revenue, expenditure, interest,
investment, Maastricht debt and stock-flow data, and act as an independent cross-check on
the balance bridge. Every workbook is parsed programmatically from the bundled file; no
value is transcribed.

{sources_table}
\subsection{{Two statistical regimes, not one series}}

The statistical splice at \textbf{{1995}} is retained explicitly and nothing is smoothed,
chained or calibrated across it. Both 1995 vintages are kept, and the revision between
them is reported in {latex.ref_table('overlap')}. The revisions are small in level terms
but non-zero for every subsector, which is why no model in this repository is fitted
across the boundary.

{overlap_table}
\subsection{{An explicit gap, not an interpolation}}

Detailed revenue and expenditure components are available for General Government from
1977 onward without interruption, but for the three subsectors only for 1977--1995 and
2000--{int(data.accounts['year'].max())}. The four intervening years are absent from the
sources and are therefore absent here; {latex.ref_figure('coverage')} shows the gap
directly.

{coverage_table}
{coverage_figure}
"""


def _section_decomposition(data: ReportInputs) -> str:
    """Build the long-run decomposition section."""
    positive_years = [
        int(value) for value in data.summary["balance_summary"]["positive_aggregate_balance_years"]
    ]
    latest = _latest(data.annual)
    year = int(latest["year"])
    selected = _view(
        data.annual.loc[data.annual["year"].isin(positive_years)],
        {
            "year": "Year",
            "general_government_balance_m_eur": "GG (M EUR)",
            "central_government_balance_m_eur": "Central (M EUR)",
            "regional_local_balance_m_eur": "Regional/local (M EUR)",
            "social_security_balance_m_eur": "SSF (M EUR)",
            "non_ssf_balance_m_eur": "Non-SSF (M EUR)",
            "ssf_offset_ratio": "Offset ratio",
        },
    )
    recent = _view(
        data.recent,
        {
            "year": "Year",
            "general_government_balance_m_eur": "GG (M EUR)",
            "central_government_balance_m_eur": "Central (M EUR)",
            "regional_local_balance_m_eur": "Regional/local (M EUR)",
            "social_security_balance_m_eur": "SSF (M EUR)",
            "non_ssf_balance_m_eur": "Non-SSF (M EUR)",
            "ssf_offset_ratio": "Offset ratio",
        },
    )
    central_negative = int(
        data.persistence.loc[data.persistence["sector"].eq("central_government"), "negative_years"].iloc[0]
    )
    ssf_positive = int(
        data.persistence.loc[data.persistence["sector"].eq("social_security_funds"), "positive_years"].iloc[0]
    )
    longrun_figure = latex.figure(
        "01_long_run_balances.png",
        caption="Net lending (+) / net borrowing (-) by subsector, as a share of GDP. The "
        "vertical rule marks the 1995 source splice.",
        label="longrun",
    )
    contributions_figure = latex.figure(
        "08_subsector_contributions.png",
        caption="The identity drawn: signed subsector contributions stacked against the "
        "General Government total. A tall column under a shallow line means the subsectors "
        "offset one another that year.",
        label="contributions",
    )
    offset_figure = latex.figure(
        "02_ssf_offset_ratio.png",
        caption="Social Security Funds offset ratio for the years in which it is defined.",
        label="offset",
    )
    positive_table = latex.table(
        selected,
        caption="Years with a positive aggregate balance.",
        label="positive",
        column_digits={"Offset ratio": 3},
        digits=0,
    )
    recent_table = latex.table(
        recent,
        caption="Subsector decomposition of the recent period.",
        label="recent",
        column_digits={"Offset ratio": 3},
        digits=0,
    )
    persistence_reference = latex.ref_table("persistence")
    identity = " + ".join(
        latex.number(float(latest[column]), 0)
        for column in (
            "central_government_balance_m_eur",
            "regional_local_balance_m_eur",
            "social_security_balance_m_eur",
        )
    )
    return rf"""\section{{Long-Run Subsector Decomposition}}
\label{{sec:decomposition}}

{longrun_figure}
Over the full panel the aggregate balance is positive in {len(positive_years)} years:
\textbf{{{_year_list(positive_years)}}}. The Central Government balance is negative in
\textbf{{{central_negative} of {data.summary['balance_validation']['n_years']} observations}},
while the Social Security balance is positive in \textbf{{{ssf_positive} observations}}
({persistence_reference} reports the full sign frequencies). These are
descriptive frequencies. They are not counterfactual statements about what the aggregate
balance would have been under a different institutional arrangement.

{contributions_figure}
\subsection{{Offset metrics}}

Writing the combined non-Social-Security balance as
\(B^{{nonSSF}}_t = B^{{C}}_t + B^{{RL}}_t\), the offset ratio is defined, whenever
\(B^{{nonSSF}}_t < 0\) and \(B^{{SSF}}_t > 0\), as
\[
O_t = \frac{{B^{{SSF}}_t}}{{\left|B^{{nonSSF}}_t\right|}}.
\]
\(O_t = 1\) means the positive Social Security balance is exactly the size of the negative
non-SSF balance. The ratio compares two recorded numbers. It is not a counterfactual, and
it does not describe what either balance would be under different institutional
arrangements. It is undefined, and left missing, whenever the signs do not make the
comparison meaningful.

In {year} the identity reads
\[
{latex.number(float(latest['general_government_balance_m_eur']), 0)} = {identity}
\quad \text{{M EUR}},
\]
with a combined non-SSF balance of
\textbf{{{latex.number(float(latest['non_ssf_balance_m_eur']), 0)} M EUR}} and an offset ratio
of \textbf{{{latest['ssf_offset_ratio']:.3f}}}.

{positive_table}
{recent_table}
{offset_figure}
"""


def _section_attribution(data: ReportInputs) -> str:
    """Build the year-to-year attribution section."""
    largest = data.attribution.reindex(
        data.attribution["aggregate_change_m_eur"].abs().sort_values(ascending=False).index
    ).head(8)
    view = _view(
        largest.sort_values("year"),
        {
            "year": "Year",
            "aggregate_change_m_eur": "Aggregate change (M EUR)",
            "central_change_m_eur": "Central (M EUR)",
            "regional_local_change_m_eur": "Regional/local (M EUR)",
            "ssf_change_m_eur": "SSF (M EUR)",
        },
    )
    attribution_table = latex.table(
        view,
        caption="The eight largest annual movements in the General Government balance, and "
        "how they decompose across subsectors.",
        label="attribution",
        digits=0,
        note="Ranked by the absolute nominal change, so the modern period dominates: "
        "nominal GDP in 2025 is orders of magnitude larger than in 1977.",
    )
    attribution_figure = latex.figure(
        "03_balance_change_attribution.png",
        caption="Annual change in the General Government balance, attributed to subsectors.",
        label="attribution",
    )
    return rf"""\section{{Year-to-Year Attribution}}
\label{{sec:attribution}}

The annual change in the aggregate balance decomposes exactly:
\[
\Delta B^{{GG}}_t = \Delta B^{{C}}_t + \Delta B^{{RL}}_t + \Delta B^{{SSF}}_t.
\]
The decomposition is stored for every adjacent year in
\path{{outputs/tables/balance_change_attribution.csv}} and closes to
\textbf{{{data.attribution['change_closure_error_m_eur'].abs().max():.2f} M EUR}} at worst.
It separates the \emph{{level}} of a subsector balance from its \emph{{contribution}} to an
annual improvement or deterioration, which are distinct questions that the level series
alone cannot answer.

{attribution_table}
{attribution_figure}
Contribution is not causation. A subsector accounting for most of an annual improvement
has not been shown to have produced it, and the 1994-to-1995 change mixes a vintage
revision with an economic movement.
"""


def _section_revenue_expenditure(data: ReportInputs) -> str:
    """Build the revenue and expenditure section."""
    changes = _view(
        _tail_years(data.revenue_expenditure, 8, sector="general_government"),
        {
            "year": "Year",
            "revenue_change_m_eur": "Change in revenue (M EUR)",
            "expenditure_change_m_eur": "Change in expenditure (M EUR)",
            "balance_change_m_eur": "Change in balance (M EUR)",
        },
    )
    residual = float(data.revenue_expenditure["decomposition_error_m_eur"].abs().max())
    changes_table = latex.table(
        changes,
        caption="Recent General Government balance changes, decomposed into revenue and "
        "expenditure changes.",
        label="revexp",
        digits=0,
    )
    revexp_figure = latex.figure(
        "04_central_revenue_expenditure.png",
        caption="Central Government revenue, expenditure and balance as shares of GDP. The "
        "line breaks at 1996--1999, where subsector components do not exist.",
        label="revexp",
    )
    return rf"""\section{{Revenue and Expenditure Dynamics}}
\label{{sec:revexp}}

For every sector-year with detailed components the balance is an identity,
\(B_{{i,t}} = R_{{i,t}} - E_{{i,t}}\), and therefore so is its change,
\[
\Delta B_{{i,t}} = \Delta R_{{i,t}} - \Delta E_{{i,t}}.
\]
The exact annual decomposition is stored in
\path{{outputs/tables/revenue_expenditure_change_decomposition.csv}} and reproduces the
recorded balance change to \textbf{{{residual:.1e} M EUR}}. Source gaps are never bridged:
no change is computed across the 1995-to-2000 discontinuity in subsector components, so
those rows are dropped rather than interpolated.

{changes_table}
{revexp_figure}
The decomposition uses totals, so a change in revenue may reflect composition shifts that
are visible only in the component columns of the account panel. It is not decomposed into
policy and macroeconomic parts, which would require assumptions this repository does not
make.
"""


def _section_social_security(data: ReportInputs) -> str:
    """Build the Social Security section."""
    latest_ssf = _latest(data.ssf)
    composition = _view(
        _tail_years(data.ssf, 6),
        {
            "year": "Year",
            "revenue_pct_gdp": "Revenue (\\% GDP)",
            "contributions_pct_gdp": "Contributions (\\% GDP)",
            "expenditure_pct_gdp": "Expenditure (\\% GDP)",
            "contributions_share_total_revenue": "Contribution share",
        },
    )
    systems = _view(
        data.ss_systems,
        {
            "year": "Year",
            "previdential_system_balance_m_eur": "Previdential (M EUR)",
            "citizenship_system_balance_m_eur": "Citizenship (M EUR)",
            "special_regimes_balance_m_eur": "Special regimes (M EUR)",
        },
    )
    latest_systems = _latest(data.ss_systems)
    latest_detail = _latest(data.ss_detail)
    composition_table = latex.table(
        composition,
        caption="Social Security Funds revenue composition, most recent years.",
        label="ssfcomposition",
        digits=2,
        column_digits={"Year": 0, "Contribution share": 3},
    )
    share_figure = latex.figure(
        "05_ssf_contribution_share.png",
        caption="Social contributions as a share of total Social Security Funds revenue.",
        label="ssfshare",
    )
    systems_table = latex.table(
        systems,
        caption="CFP Social Security budget systems: internal balances.",
        label="ssfsystems",
        digits=0,
    )
    return rf"""\section{{Social Security Funds: Revenue Composition and Internal Systems}}
\label{{sec:ssf}}

\subsection{{National-accounts view}}

The ESA 2010 Social Security Funds sector is the entity that appears in the B.9 identity.
In {int(latest_ssf['year'])}, social contributions were
\textbf{{{latest_ssf['contributions_share_total_revenue'] * 100:.2f}\%}} of total SSF
revenue in the account table.

{composition_table}
{share_figure}
\subsection{{A different boundary: the CFP budget systems}}

The CFP's Social Security report decomposes the system into the Previdential system, the
Social Protection of Citizenship system, and special regimes. These are
budget-execution aggregates with a different accounting boundary from the national
accounts, so they are reported beside the ESA 2010 balance and never added to it. In
{int(latest_systems['year'])} the reported internal balances were
\textbf{{{latex.number(float(latest_systems['previdential_system_balance_m_eur']), 0)} M EUR}}
(Previdential),
\textbf{{{latex.number(float(latest_systems['citizenship_system_balance_m_eur']), 0)} M EUR}}
(Citizenship) and
\textbf{{{latex.number(float(latest_systems['special_regimes_balance_m_eur']), 0)} M EUR}}
(special regimes).

{systems_table}
For the detailed {int(latest_detail['year'])} budget table, previdential contributions
account for \textbf{{{latest_detail['previdential_contribution_share_revenue'] * 100:.2f}\%}}
of previdential revenue. The repository does not subtract State transfers from the Social
Security balance and call the remainder an underlying balance: which transfer finances
which statutory responsibility is a legal question, not an accounting one.
"""


def _section_primary(data: ReportInputs) -> str:
    """Build the primary balance section."""
    central = _view(
        _tail_years(data.primary, 8, sector="central_government"),
        {
            "year": "Year",
            "balance_m_eur": "Balance (M EUR)",
            "interest_m_eur": "Interest (M EUR)",
            "primary_balance_recomputed_m_eur": "Primary balance (M EUR)",
            "interest_pct_gdp": "Interest (\\% GDP)",
            "primary_balance_pct_gdp": "Primary balance (\\% GDP)",
        },
    )
    latest_central = _latest(data.primary, sector="central_government")
    residual = float(data.primary["primary_balance_identity_error_m_eur"].abs().max())
    primary_table = latex.table(
        central,
        caption="Central Government headline balance, interest and primary balance.",
        label="primary",
        digits=2,
        column_digits={
            "Year": 0,
            "Balance (M EUR)": 0,
            "Interest (M EUR)": 0,
            "Primary balance (M EUR)": 0,
        },
    )
    primary_figure = latex.figure(
        "06_central_primary_balance.png",
        caption="Central Government headline balance, primary balance and interest "
        "expenditure, as shares of GDP.",
        label="primary",
    )
    return rf"""\section{{Primary Balance and Interest}}
\label{{sec:primary}}

The primary balance is reconstructed as \(PB_{{i,t}} = B_{{i,t}} + I_{{i,t}}\), where
\(I\) is interest expenditure, and then checked against the published primary-balance
row. The identity holds to \textbf{{{residual:.1e} M EUR}}, so the separation of interest
from the remaining balance is arithmetic rather than estimated.

For Central Government in {int(latest_central['year'])} the headline balance was
\textbf{{{latex.number(float(latest_central['balance_m_eur']), 0)} M EUR}}, interest expenditure
was \textbf{{{latex.number(float(latest_central['interest_m_eur']), 0)} M EUR}}, and the
recomputed primary balance was
\textbf{{{latex.number(float(latest_central['primary_balance_recomputed_m_eur']), 0)} M EUR}}.

{primary_table}
{primary_figure}
Interest is overwhelmingly a Central Government item, which is why the primary and
headline balances of the other subsectors nearly coincide. The primary balance excludes
interest by construction: it is not a measure of discretionary policy and not a
cyclically adjusted balance, and it reflects the debt stock and financing conditions
inherited from earlier periods.
"""


def _section_investment(data: ReportInputs) -> str:
    """Build the fixed-capital-formation section."""
    year = int(data.investment["year"].max())
    latest_year = _label_sectors(data.investment.loc[data.investment["year"].eq(year)])
    view = _view(
        latest_year,
        {
            "sector": "Sector",
            "balance_m_eur": "Balance (M EUR)",
            "gfcf_m_eur": "GFCF (M EUR)",
            "balance_before_gfcf_m_eur": "Balance before GFCF (M EUR)",
            "gfcf_pct_gdp": "GFCF (\\% GDP)",
        },
    )
    investment_table = latex.table(
        view,
        caption=f"Fixed-capital-formation diagnostic by sector, {year}.",
        label="investment",
        digits=2,
        column_digits={
            "Balance (M EUR)": 0,
            "GFCF (M EUR)": 0,
            "Balance before GFCF (M EUR)": 0,
        },
    )
    return rf"""\section{{Fixed-Capital-Formation Diagnostic}}
\label{{sec:investment}}

The repository reports an explicitly non-official diagnostic,
\[
B^{{before\ GFCF}}_{{i,t}} = B_{{i,t}} + GFCF_{{i,t}},
\]
which answers one narrow question: how large is public investment relative to the
recorded balance? It is not a golden-rule balance, not a structural balance, and not any
published indicator; no fiscal rule in this report is evaluated against it.

{investment_table}
Two caveats attach to the diagnostic. GFCF is gross, so no consumption of fixed capital
is netted off and the measure overstates the change in the public capital stock. And
investment is lumpy: a single-year ratio can be dominated by one project or one
reclassification.
"""


def _section_debt(data: ReportInputs) -> str:
    """Build the debt and stock-flow section."""
    general = _tail_years(data.debt, 10, sector="general_government")
    view = _view(
        general,
        {
            "year": "Year",
            "balance_m_eur": "Balance (M EUR)",
            "debt_change_m_eur": "Change in debt (M EUR)",
            "stock_flow_adjustment_m_eur": "Stock-flow adj. (M EUR)",
            "debt_pct_gdp": "Debt (\\% GDP)",
            "stock_flow_adjustment_pct_gdp": "Stock-flow adj. (\\% GDP)",
        },
    )
    latest_debt = _latest(data.debt, sector="general_government")
    debt_table = latex.table(
        view,
        caption="General Government debt and stock-flow adjustment, most recent years.",
        label="debt",
        digits=2,
        column_digits={
            "Year": 0,
            "Balance (M EUR)": 0,
            "Change in debt (M EUR)": 0,
            "Stock-flow adj. (M EUR)": 0,
        },
    )
    debt_figure = latex.figure(
        "07_general_government_debt.png",
        caption="General Government Maastricht debt and stock-flow adjustment.",
        label="debt",
    )
    return rf"""\section{{Debt and Stock-Flow Adjustment}}
\label{{sec:debt}}

Debt dynamics are not the mirror image of the annual balance. The modern CFP tables
support the reconciliation
\[
\Delta Debt_t = -B_t + SFA_t,
\]
where the stock-flow adjustment absorbs everything that changes debt without passing
through the balance: financial-asset transactions, valuation effects, timing differences
and statistical adjustments. The reconciliation closes to
\textbf{{{data.debt['reconciliation_error_m_eur'].abs().max():.1e} M EUR}}.

In {int(latest_debt['year'])}, General Government Maastricht debt was
\textbf{{{latest_debt['debt_pct_gdp']:.2f}\% of GDP}} and the stock-flow adjustment was
\textbf{{{latest_debt['stock_flow_adjustment_pct_gdp']:.2f}\% of GDP}}. In several years
the adjustment is the larger of the two terms, which is the reason for running the
reconciliation at all.

{debt_table}
{debt_figure}
The stock-flow adjustment is a residual category, not a behavioural variable: a large
value is a signal to consult the source documentation, not an anomaly in itself. The debt
ratio also moves with nominal GDP, so a falling ratio does not imply falling debt.
"""


def _section_persistence(data: ReportInputs) -> str:
    """Build the persistence and structural-break section."""
    persistence = _view(
        _label_sectors(data.persistence),
        {
            "sector": "Sector",
            "n_years": "N",
            "positive_years": "Positive",
            "negative_years": "Negative",
            "mean_balance_pct_gdp": "Mean (\\% GDP)",
            "median_balance_pct_gdp": "Median (\\% GDP)",
            "longest_positive_run": "Longest + run",
            "longest_negative_run": "Longest - run",
        },
    )
    matrix = _label_sectors(
        data.transitions.pivot_table(
            index=["sector", "state"], columns="next_state", values="probability", fill_value=0.0
        ).reset_index()
    )
    matrix.columns = [
        {"sector": "Sector", "state": "From"}.get(str(column), f"To {column}")
        for column in matrix.columns
    ]
    breaks = _view(
        _label_sectors(data.breaks),
        {
            "regime": "Regime",
            "sector": "Sector",
            "n": "N",
            "n_breaks": "Breaks",
            "break_years": "Break years",
            "segment_means_pct_gdp": "Segment means (\\% GDP)",
        },
    )
    breaks["Regime"] = breaks["Regime"].str.replace("_", " ", regex=False)
    for column in ("Break years", "Segment means (\\% GDP)"):
        breaks[column] = breaks[column].astype("string").str.replace(";", ", ", regex=False)
    persistence_table = latex.table(
        persistence,
        caption="Sign frequency, average magnitude and longest runs by subsector, over the "
        "whole panel.",
        label="persistence",
        digits=3,
        column_digits={
            "N": 0,
            "Positive": 0,
            "Negative": 0,
            "Longest + run": 0,
            "Longest - run": 0,
        },
    )
    signs_figure = latex.figure(
        "09_balance_sign_states.png",
        caption="Sign of the annual balance by subsector and year.",
        label="signs",
    )
    transitions_table = latex.table(
        matrix,
        caption="Empirical one-year sign transition frequencies. Rows sum to one.",
        label="transitions",
        digits=3,
    )
    breaks_table = latex.table(
        breaks,
        caption="Selected piecewise-constant mean shifts, by statistical regime.",
        label="breaks",
        digits=3,
        column_digits={"N": 0, "Breaks": 0},
    )
    return rf"""\section{{Persistence and Structural Mean Shifts}}
\label{{sec:persistence}}

\subsection{{Sign frequencies and runs}}

{persistence_table}
{signs_figure}
{transitions_table}
These are empirical frequencies over the transitions actually observed, not a fitted
Markov model: no standard errors and no stationarity test are claimed, and a state that
never occurs in the sample has no estimated row. Runs that span 1995 also span the
statistical splice.

\subsection{{Structural mean shifts}}

Fewer than fifty annual observations, split across two statistical regimes, do not
support a flexible change-point model. The specification is therefore deliberately
modest: a piecewise-constant mean with at most two breaks per regime, a minimum segment
length of five years, exact dynamic-programming minimisation of within-segment squared
error, and BIC selection, which may select zero breaks. Detection runs separately on
1977--1994 and 1995--{int(data.annual['year'].max())}, so the known splice is not a
candidate economic break by construction.

{breaks_table}
The detected dates are statistical summaries. This report attaches no historical cause to
any of them, and a five-year minimum segment means shifts near the end of the sample
cannot be detected yet.
"""


def _section_comovement(data: ReportInputs) -> str:
    """Build the macroeconomic co-movement section."""
    nominal = _view(
        _label_sectors(data.nominal_comovement),
        {
            "sector": "Sector",
            "n": "N",
            "r_squared": "$R^2$",
            "nominal_gdp_growth_coef": "Growth coef.",
            "nominal_gdp_growth_se_hac": "HAC s.e.",
            "nominal_gdp_growth_pvalue_hac": "HAC $p$",
            "modern_regime_coef": "Regime coef.",
        },
    )
    # A single regression reads better vertically than as one very wide row. The
    # observation count goes in the caption so the value column stays homogeneous.
    labour_labels = {
        "r_squared": "R-squared",
        "employment_growth_coef": "Employment growth coefficient",
        "employment_growth_se_hac": "Employment growth, HAC standard error",
        "employment_growth_pvalue_hac": "Employment growth, HAC p-value",
        "unemployment_rate_coef": "Unemployment rate coefficient",
        "unemployment_rate_se_hac": "Unemployment rate, HAC standard error",
        "unemployment_rate_pvalue_hac": "Unemployment rate, HAC p-value",
    }
    if data.labour_comovement.empty:
        labour_table = "Insufficient historical labour observations.\n"
    else:
        row = data.labour_comovement.iloc[0]
        labour_view = pd.DataFrame.from_records(
            [
                {"Quantity": label, "Estimate": float(row[column])}
                for column, label in labour_labels.items()
            ]
        )
        labour_table = latex.table(
            labour_view,
            caption="Historical Social Security co-movement with the labour market, "
            f"1978--1995, over {int(row['n'])} annual observations.",
            label="labour",
            digits=4,
        )
    nominal_table = latex.table(
        nominal,
        caption="Descriptive co-movement of subsector balance ratios with nominal GDP "
        "growth, HAC standard errors.",
        label="comovement",
        digits=4,
        column_digits={"N": 0},
    )
    return rf"""\section{{Descriptive Macroeconomic Co-Movement}}
\label{{sec:comovement}}

The full-period specification is
\[
B_{{i,t}}/GDP_t = \alpha_i + \beta_i g^{{nominal}}_t + \gamma_i I(t \ge 1995) +
\epsilon_{{i,t}},
\]
estimated with HAC standard errors. Nominal GDP growth is used because it is the one
macroeconomic variable that can be reconstructed on a consistent basis from the bundled
sources across the whole panel. It is deliberately not described as an output gap or as a
cyclical adjustment, and the regime indicator is a statistical control for the 1995
splice rather than an estimate of a policy change.

{nominal_table}
{labour_table}
These regressions quantify co-movement. They are not causal estimates: no identification
strategy is claimed, the sample is short and serially correlated, and HAC standard errors
address the inference arithmetic rather than small-sample or specification risk. The
labour specification rests on eighteen observations and is reported for transparency
rather than analytical weight.
"""


def _section_transfers() -> str:
    """Build the intergovernmental transfers section."""
    return r"""\section{Intergovernmental Transfers}
\label{sec:transfers}

Historical source tables identify current and capital transfers received and paid between
public administrations, which supports a mechanical sensitivity for 1977--1995:
\[
B^{sens}_{i,t} = B_{i,t} - \left(T^{received}_{i,t} - T^{paid}_{i,t}\right).
\]
The result is stored in
\path{outputs/tables/historical_transfer_reallocation_sensitivity.csv}.

It is deliberately not labelled an underlying or true balance, and it is never used to
restate B.9 anywhere in this repository. A transfer normally finances an expenditure
responsibility assigned to the recipient, so removing the transfer while leaving the
responsibility in place does not describe a coherent alternative arrangement. What the
sensitivity quantifies is how much the recorded \emph{location} of a balance depends on
the transfer convention.
"""


def _section_limitations() -> str:
    """Build the methodological limitations section."""
    return r"""\section{Methodological Limitations}
\label{sec:limitations}

\begin{enumerate}
\item \textbf{1995 is a source and methodology splice}, not an economic event. Both
vintages are retained in \path{data/interim/methodology_overlap_1995.csv} and nothing is
smoothed across the boundary.
\item \textbf{Detailed subsector accounts have no 1996--1999 observations.} No
interpolation is performed, and no statistic is computed across the gap.
\item \textbf{Nominal GDP growth is not an output gap.} The co-movement section must not
be read as a cyclically adjusted balance.
\item \textbf{Social Security national accounts and budget-system accounts have different
boundaries.} They are never merged into a single series.
\item \textbf{The fixed-investment diagnostic is not an official balance concept.}
\item \textbf{Structural-break dates are statistical summaries}, not causal event labels.
\item \textbf{Accounting contribution is not causation.} An arithmetic contribution to an
aggregate balance is not evidence about intent or responsibility.
\item \textbf{Identity and reconciliation residuals validate the extraction}, not the
underlying official statistics.
\item All interpretation is restricted to accounting, statistical and economic
relationships directly supported by the bundled data.
\end{enumerate}
"""


def _section_reproducibility(data: ReportInputs) -> str:
    """Build the reproducibility section and the artefact appendix."""
    index = pd.DataFrame.from_records(
        [
            {"Section": section, "Notebook": notebook, "Primary artefact": artefact}
            for section, notebook, artefact in ARTEFACT_INDEX
        ]
    )
    index_table = latex.table(
        index,
        caption="Report sections mapped to the notebook that produces them and the primary "
        "persisted artefact they read.",
        label="artefacts",
        mono_columns={"Notebook", "Primary artefact"},
        note="Notebook names omit the \\path{notebooks/} prefix and the \\path{.ipynb} "
        "suffix. Figures are read from \\path{outputs/figures/}.",
    )
    return rf"""\section{{Reproducibility}}
\label{{sec:reproducibility}}

The repository preserves the raw source workbooks, source-specific intermediate CSVs, the
canonical processed panels, every calculated analysis table, the figures, the executed
notebooks and a SHA-256 digest of each bundled raw file. The default rebuild is

\begin{{verbatim}}
poetry install
make all
\end{{verbatim}}

which runs the deterministic pipeline, executes the notebooks with their outputs stored in
place, and runs the test suite. This document is regenerated from the persisted outputs
rather than from hard-coded conclusions, and it is built from repository version
\textbf{{{data.version}}}.

\appendix
\section{{Artefact Index}}
\label{{sec:artefacts}}

Each section of this report is produced by a notebook and reads a persisted artefact.

{index_table}
"""


_METRIC_LABELS: dict[str, str] = {
    "general_government_balance_m_eur": "General Government",
    "central_government_balance_m_eur": "Central Government",
    "regional_local_balance_m_eur": "Regional and Local",
    "social_security_balance_m_eur": "Social Security Funds",
}


def render_report(root: Path) -> Path:
    """Generate report/report.tex using only outputs already written by the pipeline."""
    data = load(root)
    document = "\n".join(
        [
            latex.preamble(
                title=TITLE,
                author=AUTHOR,
                subject=SUBJECT,
                date=rf"Repository version {data.version}",
            ),
            r"\begin{document}",
            r"\maketitle",
            _abstract(data),
            _section_glance(data),
            _section_data(data),
            _section_decomposition(data),
            _section_attribution(data),
            _section_revenue_expenditure(data),
            _section_social_security(data),
            _section_primary(data),
            _section_investment(data),
            _section_debt(data),
            _section_persistence(data),
            _section_comovement(data),
            _section_transfers(),
            _section_limitations(),
            _section_reproducibility(data),
            r"\end{document}",
            "",
        ]
    )

    report_dir = root / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    stale_markdown = report_dir / "report.md"
    if stale_markdown.exists():
        stale_markdown.unlink()

    output = report_dir / "report.tex"
    output.write_text(document, encoding="utf-8")
    return output

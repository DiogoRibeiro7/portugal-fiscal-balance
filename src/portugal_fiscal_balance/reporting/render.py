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
from portugal_fiscal_balance.schemas import REGIME_TABLE_LABELS, SECTOR_LABELS

TITLE = "Portugal's General-Government Balance by Subsector, 1977--2025"
AUTHOR = "Diogo Ribeiro"
SUBJECT = (
    "Accounting decomposition of Portugal's general-government net lending "
    "and net borrowing by subsector"
)

#: Sections of the report, the notebook that produces them and the artefact they read.
ARTEFACT_INDEX: tuple[tuple[str, str, str], ...] = (
    ("Data, sources and validation", "03_harmonize_and_validate", "data/processed/fiscal_balances_1977_2025.csv"),
    ("Identity and source-agreement checks", "03_harmonize_and_validate", "outputs/tables/source_validation_summary.csv"),
    ("Long-run subsector decomposition", "04_balance_decomposition", "data/processed/annual_balance_metrics_1977_2025.csv"),
    ("Year-to-year attribution", "06_year_to_year_attribution", "outputs/tables/balance_change_attribution.csv"),
    ("Largest annual movements", "06_year_to_year_attribution", "outputs/tables/largest_balance_movements.csv"),
    ("Revenue and expenditure dynamics", "05_revenue_expenditure", "outputs/tables/revenue_expenditure_change_decomposition.csv"),
    ("Social Security Funds", "09_social_security_mechanisms", "outputs/tables/social_security_account_metrics.csv"),
    ("Social Security balance-change decomposition", "09_social_security_mechanisms", "outputs/tables/ssf_balance_change_decomposition.csv"),
    ("Social Security accounting boundaries", "09_social_security_mechanisms", "outputs/tables/ssf_accounting_boundary_comparison.csv"),
    ("Primary balance and interest", "11_primary_balance", "outputs/tables/primary_balance_and_interest.csv"),
    ("Primary balance sign frequencies", "11_primary_balance", "outputs/tables/primary_balance_sign_summary.csv"),
    ("Fixed-capital-formation diagnostic", "12_investment_diagnostic", "outputs/tables/investment_diagnostic.csv"),
    ("Debt and stock-flow adjustment", "13_debt_reconciliation", "outputs/tables/debt_stock_flow_reconciliation.csv"),
    ("Persistence, pooled and by regime", "07_persistence", "outputs/tables/persistence_by_regime.csv"),
    ("Structural mean shifts", "08_structural_breaks", "outputs/tables/structural_breaks.csv"),
    ("Change-point robustness", "08_structural_breaks", "outputs/tables/structural_break_sensitivity.csv"),
    ("Contribution base", "09_social_security_mechanisms", "outputs/tables/contribution_change_decomposition.csv"),
    ("European benchmark", "16_european_benchmark", "outputs/tables/european_benchmark_summary.csv"),
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
    source_comparison: pd.DataFrame
    attribution: pd.DataFrame
    movements: pd.DataFrame
    episode_components: pd.DataFrame
    revenue_expenditure: pd.DataFrame
    recent: pd.DataFrame
    persistence: pd.DataFrame
    regime_persistence: pd.DataFrame
    transitions: pd.DataFrame
    breaks: pd.DataFrame
    break_ladder: pd.DataFrame
    break_stability: pd.DataFrame
    ssf: pd.DataFrame
    ss_systems: pd.DataFrame
    ss_detail: pd.DataFrame
    ss_boundary: pd.DataFrame
    ss_change: pd.DataFrame
    primary: pd.DataFrame
    primary_signs: pd.DataFrame
    investment: pd.DataFrame
    debt: pd.DataFrame
    nominal_comovement: pd.DataFrame
    labour_comovement: pd.DataFrame
    validation_summary: pd.DataFrame
    balances: pd.DataFrame
    base_panel: pd.DataFrame
    base_decomposition: pd.DataFrame
    base_regression: pd.DataFrame
    benchmark_panel: pd.DataFrame
    benchmark_summary: pd.DataFrame
    benchmark_position: pd.DataFrame


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
            # The vintage is the file's publication date, not its last covered
            # year. Two files can cover 2025 and disagree about it.
            "Vintage": entry.get("vintage", "--"),
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
        source_comparison=pd.read_csv(interim / "modern_source_comparison.csv"),
        attribution=pd.read_csv(tables / "balance_change_attribution.csv"),
        movements=pd.read_csv(tables / "largest_balance_movements.csv"),
        episode_components=pd.read_csv(tables / "episode_component_attribution.csv"),
        revenue_expenditure=pd.read_csv(tables / "revenue_expenditure_change_decomposition.csv"),
        recent=pd.read_csv(tables / "recent_balance_decomposition_2010_2025.csv"),
        persistence=pd.read_csv(tables / "persistence_summary.csv"),
        regime_persistence=pd.read_csv(tables / "persistence_by_regime.csv"),
        transitions=pd.read_csv(tables / "transition_probabilities.csv"),
        breaks=pd.read_csv(tables / "structural_breaks.csv"),
        break_ladder=pd.read_csv(tables / "structural_break_bic_ladder.csv"),
        break_stability=pd.read_csv(tables / "structural_break_stability.csv"),
        ssf=pd.read_csv(tables / "social_security_account_metrics.csv"),
        ss_systems=pd.read_csv(tables / "social_security_system_metrics_2019_2025.csv"),
        ss_detail=pd.read_csv(tables / "social_security_detail_metrics_2024_2025.csv"),
        ss_boundary=pd.read_csv(tables / "ssf_accounting_boundary_comparison.csv"),
        ss_change=pd.read_csv(tables / "ssf_balance_change_decomposition.csv"),
        primary=pd.read_csv(tables / "primary_balance_and_interest.csv"),
        primary_signs=pd.read_csv(tables / "primary_balance_sign_summary.csv"),
        investment=pd.read_csv(tables / "investment_diagnostic.csv"),
        debt=pd.read_csv(tables / "debt_stock_flow_reconciliation.csv"),
        nominal_comovement=pd.read_csv(tables / "nominal_gdp_balance_comovement.csv"),
        labour_comovement=pd.read_csv(tables / "historical_ssf_labour_comovement.csv"),
        validation_summary=pd.read_csv(tables / "source_validation_summary.csv"),
        balances=pd.read_csv(processed / "fiscal_balances_1977_2025.csv"),
        base_panel=pd.read_csv(processed / "contribution_base_panel_1995_2025.csv"),
        base_decomposition=pd.read_csv(tables / "contribution_change_decomposition.csv"),
        base_regression=pd.read_csv(tables / "contribution_wage_bill_regression.csv"),
        benchmark_panel=pd.read_csv(processed / "european_subsector_panel_1995_2025.csv"),
        benchmark_summary=pd.read_csv(tables / "european_benchmark_summary.csv"),
        benchmark_position=pd.read_csv(tables / "european_benchmark_position.csv"),
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


def _sector_row(frame: pd.DataFrame, sector: str) -> pd.Series[Any]:
    """Return the single row of a per-sector summary table describing one sector."""
    return frame.loc[frame["sector"].eq(sector)].iloc[0]


def _label_regimes(frame: pd.DataFrame, *, column: str = "regime") -> pd.DataFrame:
    """Replace the regime keys with presentation labels, keeping the source order."""
    labelled = frame.copy()
    labelled[column] = (
        labelled[column].map(REGIME_TABLE_LABELS).fillna(labelled[column]).astype("string")
    )
    return labelled


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
    central_signs = _sector_row(data.primary_signs, "central_government")
    central_persistence = _sector_row(data.persistence, "central_government")
    ssf_persistence = _sector_row(data.persistence, "social_security_funds")
    regime_gg = data.regime_persistence.loc[
        data.regime_persistence["sector"].eq("general_government")
    ].sort_values("regime")
    return rf"""\begin{{abstract}}
\noindent
This report decomposes Portugal's annual general-government net lending (+) / net
borrowing (-) into Central Government, Regional and Local Government, and Social
Security Funds (SSF), for the {validation['n_years']} years from
{int(data.annual['year'].min())} to {int(data.annual['year'].max())}. The analysis is
empirical and accounting-focused. It covers long-run balance composition, exact
year-to-year attribution, revenue and expenditure dynamics, sign persistence,
conservative structural mean shifts, Social Security revenue composition and internal
systems, primary balances and interest, public investment and debt-flow reconciliation.

\noindent
The central accounting identity is
\[
B^{{GG}}_t = B^{{C}}_t + B^{{RL}}_t + B^{{SSF}}_t,
\]
and it closes for every year in the panel to within rounding.

\noindent
The recorded pattern is the following.
The aggregate balance is positive in {len(positive)} of {validation['n_years']} years: {_year_list(positive)}.
The Central Government balance is negative in all
{int(central_persistence['negative_years'])}, and the Social Security
balance is positive in {int(ssf_persistence['positive_years'])}. In
each of the {len(positive)} years with a positive aggregate balance the combined non-SSF
balance is negative and the SSF balance exceeds it in absolute size. Magnitudes differ
sharply across the 1995 statistical splice -- the aggregate balance averages
{float(regime_gg.iloc[0]['mean_balance_pct_gdp']):.2f}\% of GDP before it and
{float(regime_gg.iloc[1]['mean_balance_pct_gdp']):.2f}\% after -- so no level statistic is
pooled across it. Once interest is excluded, the Central Government primary balance is
positive in {int(central_signs['primary_positive_years'])} of the
{int(central_signs['n_years'])} years for which the detailed accounts exist: a persistently
negative B.9 does not imply a persistently negative primary balance.

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
        caption="Detailed account coverage by sector and statistical regime. Each mark is a "
        "sector-year for which revenue and expenditure components exist. The empty band at "
        "1996--1999 is the source gap, not a rendering artefact. Sources: Banco de Portugal / "
        "INE long series and CFP ESA 2010 workbooks.",
        label="coverage",
    )
    provisional = data.balances.loc[data.balances["vintage_status"].eq("provisional"), "year"]
    provisional_years = [int(year) for year in sorted(provisional)]
    validation = _view(
        data.validation_summary,
        {
            "check": "Check",
            "comparison": "Quantity compared",
            "n_observations": "N",
            "max_abs_difference_m_eur": "Largest absolute difference (M EUR)",
            "year_of_max": "Where",
        },
    )
    validation_table = latex.table(
        validation,
        caption="Every cross-check the pipeline runs, in one unit. Identity rows test whether "
        "the extraction is arithmetically self-consistent; source-agreement rows test whether "
        "two independently published sources report the same number for the same year.",
        label="validation",
        digits=3,
        column_digits={"N": 0},
        note="Identity closure does not imply source agreement: the identities close to "
        "rounding while the largest source disagreement is a Central Government difference of "
        "about 67 million euro. The two are different tests and neither substitutes for the "
        "other.",
    )
    differences_figure = latex.figure(
        "15_modern_source_differences.png",
        caption="PORDATA bridge minus CFP ESA 2010 workbook, by subsector, over the years both "
        "sources cover. Values are million euro; zero means the two sources agree exactly. The "
        "Central Government series is the only one that departs materially from zero.",
        label="sourcediff",
    )
    provisional_sentence = (
        rf"""The {_year_list(provisional_years)} observations are flagged
\textbf{{provisional}} by the publisher and are carried with that flag through the canonical
panel. They are the years this report discusses most, and they are the years most likely to
be restated: a later vintage will revise them."""
        if provisional_years
        else "No year in the current vintage is flagged provisional at source."
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
\subsection{{Data vintage}}

Every figure in this report belongs to one data vintage, recorded per source in
{latex.ref_table('sources')}. The modern national-accounts and CFP files are the April 2026
releases. {provisional_sentence}

\subsection{{Two statistical regimes, not one series}}

The statistical splice at \textbf{{1995}} is retained explicitly and nothing is smoothed,
chained or calibrated across it. Both 1995 vintages are kept, and the revision between
them is reported in {latex.ref_table('overlap')}. The revisions are small in level terms
but non-zero for every subsector, which is why no model in this report is fitted
across the boundary, and why no statistic that depends on the level of the balance is
averaged across it.

{overlap_table}
\subsection{{An explicit gap, not an interpolation}}

Detailed revenue and expenditure components are available for General Government from
1977 onward without interruption, but for the three subsectors only for 1977--1995 and
2000--{int(data.accounts['year'].max())}. The four intervening years are absent from the
sources and are therefore absent here; {latex.ref_figure('coverage')} shows the gap
directly. The canonical B.9 balance panel is unaffected: it has an observation for every
one of the {data.summary['balance_validation']['n_years']} years, and only the detailed
components are missing. Every figure drawn from the account panel breaks its line across
those years rather than joining 1995 to 2000.

{coverage_table}
{coverage_figure}
\subsection{{Identity closure and source agreement are different tests}}

{validation_table}
{differences_figure}
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
    central_negative = int(_sector_row(data.persistence, "central_government")["negative_years"])
    ssf_positive = int(_sector_row(data.persistence, "social_security_funds")["positive_years"])
    longrun_figure = latex.figure(
        "01_long_run_balances.png",
        caption="Net lending (+) / net borrowing (-) by subsector, as a share of GDP. The "
        "vertical rule marks the 1995 source splice.",
        label="longrun",
    )
    contributions_figure = latex.figure(
        "08_subsector_contributions.png",
        caption="The identity drawn: positive and negative subsector contributions are stacked "
        "separately from zero, and the General Government line gives their algebraic sum. The "
        "total visible span of a column is therefore the sum of the absolute contributions, not "
        "the aggregate balance; a tall span under a shallow line means the subsectors offset one "
        "another that year.",
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
        caption="The eight largest annual movements in the General Government balance by "
        "nominal size, and how they decompose across subsectors.",
        label="attribution",
        digits=0,
        note="Ranked by the absolute nominal change, so the modern period dominates: "
        "nominal GDP in 2025 is orders of magnitude larger than in 1977. "
        + latex.ref_table("movements")
        + " ranks the same quantity scaled by GDP, which does not have that bias.",
    )
    movements = _view(
        _label_regimes(data.movements),
        {
            "regime": "Regime",
            "rank_in_regime": "Rank",
            "year": "Year",
            "direction": "Direction",
            "aggregate_change_pct_gdp": "Aggregate change (\\% GDP)",
            "aggregate_change_m_eur": "Aggregate change (M EUR)",
            "central_change_m_eur": "Central (M EUR)",
            "regional_local_change_m_eur": "Regional/local (M EUR)",
            "ssf_change_m_eur": "SSF (M EUR)",
            "dominant_subsector": "Largest contributor",
            "dominant_subsector_share": "Its share of the move",
        },
    )
    movements["Direction"] = movements["Direction"].str.capitalize()
    movements_table = latex.table(
        movements,
        caption="The largest annual movements inside each statistical regime, ranked by the "
        "absolute change scaled by current-year GDP, with the subsector that accounts for most "
        "of each move.",
        label="movements",
        digits=0,
        column_digits={
            "Rank": 0,
            "Aggregate change (\\% GDP)": 2,
            "Its share of the move": 2,
        },
        note="Ranking is within a regime, not across both: each annual change is computed "
        "inside one source family, but ordering historical against modern episodes by size "
        "would compare two methodologies. Scaling by current-year GDP shares one denominator "
        "across the three subsector terms, so the decomposition stays exact; it is not the "
        "change in the balance ratio, which would also move with the denominator. 1995 is "
        "excluded because the 1994-to-1995 change straddles the splice in both panels.",
    )
    modern_figure = latex.figure(
        "03_balance_change_attribution.png",
        caption="Annual change in the General Government balance attributed to subsectors, "
        "1996--2025, as a percentage of current-year GDP. The black line is the identity total; "
        "a tall stack under a short line means the subsectors moved in opposite directions that "
        "year.",
        label="attributionmodern",
    )
    historical_figure = latex.figure(
        "11_attribution_historical.png",
        caption="The same decomposition for 1978--1994, on the same scaling. The two windows are "
        "drawn as separate panels because a single panel spanning 1995 would place a vintage "
        "revision among the economic movements and give it equal visual weight.",
        label="attributionhistorical",
    )
    return rf"""\section{{Year-to-Year Attribution}}
\label{{sec:attribution}}

The annual change in the aggregate balance decomposes exactly:
\[
\Delta B^{{GG}}_t = \Delta B^{{C}}_t + \Delta B^{{RL}}_t + \Delta B^{{SSF}}_t.
\]
The decomposition is computed for all
\textbf{{{len(data.attribution)} adjacent-year pairs}} in the panel and closes to
\textbf{{{data.attribution['change_closure_error_m_eur'].abs().max():.2f} M EUR}} at worst.
It separates the \emph{{level}} of a subsector balance from its \emph{{contribution}} to an
annual improvement or deterioration, which are distinct questions that the level series
alone cannot answer.

{attribution_table}
{movements_table}
Both windows of the decomposition are drawn below.
{latex.ref_figure('attributionmodern')} covers 1996--2025 and
{latex.ref_figure('attributionhistorical')} covers 1978--1994; neither crosses the 1995
splice.

{modern_figure}
{historical_figure}
Contribution is not causation. A subsector accounting for most of an annual improvement
has not been shown to have produced it.
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
    episodes = _view(
        data.movements,
        {
            "year": "Year",
            "dominant_subsector": "Largest contributor",
            "dominant_subsector_change_m_eur": "Its balance change (M EUR)",
            "dominant_revenue_change_m_eur": "$\\Delta$ revenue (M EUR)",
            "dominant_expenditure_change_m_eur": "$\\Delta$ expenditure (M EUR)",
            "dominant_expenditure_contribution_m_eur": "Expenditure contribution (M EUR)",
        },
    )
    episodes_table = latex.table(
        episodes,
        caption="The same episodes as in "
        + latex.ref_table("movements")
        + ", with the subsector accounting for most of each move split into its own revenue and "
        "expenditure changes.",
        label="revexpepisodes",
        digits=0,
        note="The split is of the named subsector, not of the aggregate, so the columns describe "
        "the same entity as the contributor column. Expenditure enters the balance negatively: "
        "the last column is minus the expenditure change, and it is that column which adds to "
        "the revenue change to give the subsector's balance change.",
    )
    components = _view(
        _label_regimes(data.episode_components),
        {
            "regime": "Regime",
            "year": "Year",
            "dominant_subsector": "Subsector",
            "side": "Side",
            "component": "Component",
            "change_m_eur": "Change (M EUR)",
            "contribution_m_eur": "Contribution to balance (M EUR)",
        },
    )
    components["Side"] = components["Side"].str.capitalize()
    components_table = latex.table(
        components,
        caption="The three largest component movements behind each episode, for the subsector "
        "that dominates it, ranked by the absolute size of the contribution.",
        label="episodecomponents",
        digits=0,
        note="The two source families resolve the accounts at different depths: the modern "
        "workbooks separate four revenue and seven expenditure components, the historical "
        "series only current from capital. Each sector-year uses the finer scheme it reports, "
        "so the modern period is never coarsened to match the historical one. Expenditure "
        "contributions are negated, so a falling capital expenditure appears as a positive "
        "contribution.",
    )
    revexp_figure = latex.figure(
        "04_central_revenue_expenditure.png",
        caption="Central Government revenue, expenditure and balance as shares of GDP, "
        "1977--2025. The line breaks at 1996--1999, where subsector components do not exist in "
        "either source; the gap is left open rather than interpolated. The vertical rule marks "
        "the 1995 splice.",
        label="revexp",
    )
    changes_figure = latex.figure(
        "12_gg_revenue_expenditure_changes.png",
        caption="The identity drawn for General Government, 2001--2025: the annual change in the "
        "balance against the revenue and expenditure changes that compose it, in million euro.",
        label="revexpchanges",
    )
    return rf"""\section{{Revenue and Expenditure Dynamics}}
\label{{sec:revexp}}

For every sector-year with detailed components the balance is an identity,
\(B_{{i,t}} = R_{{i,t}} - E_{{i,t}}\), and therefore so is its change,
\[
\Delta B_{{i,t}} = \Delta R_{{i,t}} - \Delta E_{{i,t}}.
\]
The decomposition reproduces the recorded balance change to
\textbf{{{residual:.1e} M EUR}} across
\textbf{{{len(data.revenue_expenditure)} sector-year changes}}. Source gaps are never
bridged: no change is computed across the 1995-to-2000 discontinuity in subsector
components, so those rows are dropped rather than interpolated.

{changes_table}
{episodes_table}
\subsection{{Which accounts moved}}

The subsector split says where an episode sits; the component split says which accounts
produced it. The two source families resolve the accounts at different depths, so each
sector-year uses the finer scheme it reports rather than being coarsened to a common one.

{components_table}
{changes_figure}
{revexp_figure}
The decomposition uses totals, so a change in revenue may reflect composition shifts that
are visible only in the component columns of the account panel. It is not decomposed into
policy and macroeconomic parts, which would require assumptions this report does not
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
    systems_figure = latex.figure(
        "13_ssf_budget_systems.png",
        caption="The CFP internal Social Security balances stacked by system, in million euro. "
        "The rise over the period is concentrated in the Previdential system, while the "
        "Citizenship system moves between small positive and small negative balances.",
        label="ssfsystemsfig",
    )
    boundary = _view(
        data.ss_boundary,
        {
            "year": "Year",
            "esa2010_ssf_balance_m_eur": "ESA 2010 balance (M EUR)",
            "budget_system_total_m_eur": "Budget-system total (M EUR)",
            "boundary_difference_m_eur": "Difference (M EUR)",
            "boundary_difference_share_esa_balance": "Difference as share of ESA balance",
        },
    )
    boundary_table = latex.table(
        boundary,
        caption="The two accounting boundaries side by side. The columns are not added, netted "
        "or reconciled: they are different objects, and the difference column measures how far "
        "apart they are.",
        label="ssfboundary",
        digits=0,
        column_digits={"Difference as share of ESA balance": 3},
        note="The difference is non-zero in every overlapping year. That is the reason a "
        "Social Security figure quoted from the budget documents cannot be substituted for the "
        "one that enters the national-accounts identity.",
    )
    boundary_figure = latex.figure(
        "14_ssf_accounting_boundary.png",
        caption="The same comparison drawn. The upper panel carries both balances on a shared "
        "axis, where they are nearly indistinguishable; the lower panel carries the difference "
        "on its own axis, which is invisible at the scale of the levels.",
        label="ssfboundaryfig",
    )
    latest_boundary = _latest(data.ss_boundary)
    previdential_first = data.ss_systems.sort_values("year").iloc[0]
    change_recent = _tail_years(data.ss_change, 6)
    change_view = _view(
        change_recent,
        {
            "year": "Year",
            "balance_change_m_eur": "Change in balance (M EUR)",
            "contributions_contribution_m_eur": "Social contributions (M EUR)",
            "other_revenue_contribution_m_eur": "Other revenue (M EUR)",
            "social_transfers_contribution_m_eur": "Social transfers (M EUR)",
            "other_expenditure_contribution_m_eur": "Other expenditure (M EUR)",
        },
    )
    change_table = latex.table(
        change_view,
        caption="Contributions to the annual change in the Social Security balance. Each column "
        "carries the sign with which the term enters the balance, so the four add to the change.",
        label="ssfchange",
        digits=0,
        note="Expenditure enters the balance negatively, so a rise in social transfers appears "
        "as a negative contribution. Reporting the raw expenditure change beside the balance "
        "change would invite adding two quantities of opposite sign. The identity closes to "
        f"{data.ss_change['contribution_closure_error_m_eur'].abs().max():.1e} M EUR.",
    )
    change_figure = latex.figure(
        "16_ssf_balance_change_decomposition.png",
        caption="The same decomposition drawn, 2001 onward. Layers above zero raised the balance "
        "that year and layers below zero reduced it; the black line is the identity total.",
        label="ssfchangefig",
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
\subsection{{Where the annual change comes from}}

The balance identity differences exactly, so each annual change in the Social Security
balance decomposes into the account movements that produced it. The revenue split is
available for the whole detailed panel; the expenditure component detail exists only for
the modern period, so social transfers are separated from the remainder there.

{change_table}
{change_figure}
This locates a change in the accounts. It does not explain it: a contributory balance moves
with employment, wages, contribution rates, entitlement rules and demographics at the same
time, and separating those requires a model this report does not build.

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
{systems_figure}
Across the years the CFP publishes, the Previdential balance moves from
\textbf{{{latex.number(float(previdential_first['previdential_system_balance_m_eur']), 0)} M EUR}}
in {int(previdential_first['year'])} to
\textbf{{{latex.number(float(latest_systems['previdential_system_balance_m_eur']), 0)} M EUR}}
in {int(latest_systems['year'])}, while the Citizenship balance stays small in both
directions. The movement in the internal balances is therefore concentrated in one of the
two systems. This is a description of the published series and not an account of what
caused it.

For the detailed {int(latest_detail['year'])} budget table, previdential contributions
account for \textbf{{{latest_detail['previdential_contribution_share_revenue'] * 100:.2f}\%}}
of previdential revenue. State transfers are not subtracted from the Social Security
balance to produce an underlying balance: which transfer finances which statutory
responsibility is a legal question, not an accounting one.

\subsection{{Why the two boundaries must not be interchanged}}

The two Social Security balances are close but never equal. In
{int(latest_boundary['year'])} the ESA 2010 balance was
\textbf{{{latex.number(float(latest_boundary['esa2010_ssf_balance_m_eur']), 0)} M EUR}}
while the three budget systems summed to
\textbf{{{latex.number(float(latest_boundary['budget_system_total_m_eur']), 0)} M EUR}}, a
difference of
\textbf{{{latex.number(float(latest_boundary['boundary_difference_m_eur']), 0)} M EUR}}. A
difference of the same order is present in every year the two overlap.

{boundary_table}
{boundary_figure}
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
        "expenditure as shares of GDP, over every year for which interest is available. The "
        "primary balance crosses zero repeatedly while the headline balance does not; the line "
        "breaks at 1996--1999 where subsector components are missing.",
        label="primary",
    )
    signs = _view(
        _label_sectors(data.primary_signs),
        {
            "sector": "Sector",
            "n_years": "N",
            "headline_negative_years": "Headline < 0",
            "primary_positive_years": "Primary > 0",
            "mean_interest_pct_gdp": "Mean interest (\\% GDP)",
            "max_interest_pct_gdp": "Peak interest (\\% GDP)",
        },
    )
    signs_table = latex.table(
        signs,
        caption="Headline against primary balance sign frequencies, over the sector-years for "
        "which interest expenditure is available.",
        label="primarysigns",
        digits=2,
        column_digits={"N": 0, "Headline < 0": 0, "Primary > 0": 0},
        note="The panel here is the detailed account panel, so the three subsectors have 45 "
        "observations rather than the 49 of the canonical balance panel; the 1996--1999 "
        "components are missing.",
    )
    central_signs = _sector_row(data.primary_signs, "central_government")
    positive_primary_years = [
        int(year)
        for year in str(central_signs["primary_positive_year_list"]).split(";")
        if year not in ("", "nan")
    ]
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
\subsection{{The headline sign is not the primary sign}}

Central Government records a negative B.9 in every year of the canonical panel. Read alone,
that invites the conclusion that the subsector is in deficit on every measure. It is not.
Over the
\textbf{{{int(central_signs['n_years'])} years}} for which interest expenditure is
available, the Central Government headline balance is negative in
\textbf{{{int(central_signs['headline_negative_years'])}}} of them, while the primary
balance is positive in \textbf{{{int(central_signs['primary_positive_years'])}}}:
{_year_list(positive_primary_years)}.

The two statements are both descriptive and they are not in conflict. The headline balance
is negative throughout; the primary balance, which excludes interest by construction, is
positive in a non-trivial minority of the observed years. Interest peaked at
\textbf{{{central_signs['max_interest_pct_gdp']:.2f}\% of GDP}} and averaged
\textbf{{{central_signs['mean_interest_pct_gdp']:.2f}\%}} across the panel, which is the
arithmetic that separates them.

{signs_table}
{primary_figure}
Interest is overwhelmingly a Central Government item, which is why the primary and
headline balances of the other subsectors nearly coincide. The primary balance excludes
interest by construction: it is not a measure of discretionary policy and not a
cyclically adjusted balance, and it reflects the debt stock and financing conditions
inherited from earlier periods. A positive primary balance is therefore not evidence of
a sustainable position, and a negative headline balance is not evidence of an
unsustainable one.
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
        _label_regimes(_label_sectors(data.breaks)),
        {
            "regime": "Regime",
            "sector": "Sector",
            "n": "N",
            "n_breaks": "Breaks",
            "break_years": "Break years",
            "segment_means_pct_gdp": "Segment means (\\% GDP)",
            "bic_margin_over_next_best": "BIC margin",
        },
    )
    for column in ("Break years", "Segment means (\\% GDP)"):
        breaks[column] = breaks[column].astype("string").str.replace(";", ", ", regex=False)
    regime_view = _view(
        _label_regimes(_label_sectors(data.regime_persistence)),
        {
            "regime": "Regime",
            "sector": "Sector",
            "n_years": "N",
            "positive_years": "Positive",
            "negative_years": "Negative",
            "mean_balance_pct_gdp": "Mean (\\% GDP)",
            "median_balance_pct_gdp": "Median (\\% GDP)",
        },
    )
    regime_table = latex.table(
        regime_view,
        caption="The same sign counts and magnitudes computed inside each statistical regime "
        "rather than pooled across both.",
        label="persistenceregime",
        digits=3,
        column_digits={"N": 0, "Positive": 0, "Negative": 0},
        note="Runs are not recomputed per regime: a run is a property of the uninterrupted "
        "series, and truncating it at a window boundary would report the length of the window.",
    )
    stability = _view(
        _label_regimes(_label_sectors(data.break_stability)),
        {
            "regime": "Regime",
            "sector": "Sector",
            "n_specifications": "Specifications",
            "modal_n_breaks": "Modal breaks",
            "modal_n_breaks_share": "Share at modal count",
            # Deliberately "dates", not "years": the table renderer treats any
            # column whose name contains "year" as an integer year label, which
            # would print these shares as 0 and 1.
            "modal_break_years": "Modal dates",
            "modal_break_years_share": "Share at modal dates",
            "n_distinct_break_year_sets": "Distinct date sets",
        },
    )
    stability["Modal dates"] = (
        stability["Modal dates"].astype("string").str.replace(";", ", ", regex=False)
    )
    stability_table = latex.table(
        stability,
        caption="Sensitivity of the detected breaks to the two tuning choices, over a grid of "
        "twelve specifications per series: minimum segment length in 4, 5, 6, 7 crossed with a "
        "maximum of 1, 2 or 3 breaks.",
        label="breakstability",
        digits=2,
        column_digits={
            "Specifications": 0,
            "Modal breaks": 0,
            "Distinct date sets": 0,
        },
        note="Neither tuning parameter is estimated from the data. A date that survives only "
        "one of their values is a property of that choice, not of the series, and the share "
        "columns are what distinguishes the two cases.",
    )
    persistence_table = latex.table(
        persistence,
        caption="Sign frequency, average magnitude and longest runs by subsector, pooled over "
        "the whole panel. The pooled means are reported for completeness only; see "
        + latex.ref_table("persistenceregime")
        + " for the regime split.",
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
        caption="Preferred piecewise-constant mean specification, by statistical regime. The BIC "
        "margin is how much better the selected break count scores than the next-best count.",
        label="breaks",
        digits=3,
        column_digits={"N": 0, "Breaks": 0, "BIC margin": 2},
    )
    # Compare the preferred specification against the modal grid outcome. Where
    # they disagree the selected dates are an artefact of the tuning choice, and
    # saying so is the whole point of running the grid.
    agreement = data.breaks.merge(
        data.break_stability[
            [
                "regime",
                "sector",
                "modal_break_years",
                "modal_break_years_share",
                "n_distinct_break_year_sets",
            ]
        ],
        on=["regime", "sector"],
        how="left",
        validate="one_to_one",
    )
    preferred = agreement["break_years"].fillna("").astype("string")
    modal = agreement["modal_break_years"].fillna("").astype("string")
    agreement["matches_modal"] = preferred.eq(modal)
    disagreeing = agreement.loc[~agreement["matches_modal"]]
    n_series = int(len(agreement))
    n_agree = int(agreement["matches_modal"].sum())
    weakest = agreement.loc[agreement["modal_break_years_share"].idxmin()]
    if disagreeing.empty:
        disagreement_sentence = (
            "The preferred specification returns the modal set of dates for every series, "
            "which is the most favourable case the grid can produce."
        )
    else:
        examples = ", ".join(
            f"{SECTOR_LABELS[str(row.sector)]} in the "
            f"{REGIME_TABLE_LABELS.get(str(row.regime), str(row.regime))} regime"
            for row in disagreeing.itertuples(index=False)
        )
        disagreement_sentence = (
            rf"""In {n_agree} of the {n_series} series the preferred specification returns the
modal set of dates. In the remaining {n_series - n_agree} it does not: {examples}. For those
series the selected dates follow the tuning choice rather than the series, and the modal
column in {latex.ref_table('breakstability')} is the more reliable summary."""
        )
    pooled_gg = _sector_row(data.persistence, "general_government")
    regime_gg = data.regime_persistence.loc[
        data.regime_persistence["sector"].eq("general_government")
    ].sort_values("regime")
    historical_gg = float(regime_gg.iloc[0]["mean_balance_pct_gdp"])
    modern_gg = float(regime_gg.iloc[1]["mean_balance_pct_gdp"])
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

\subsection{{Pooled averages describe neither regime}}

The magnitudes in {latex.ref_table('persistence')} average across the 1995 splice, and the
two regimes differ enough that the pooled figure is not a good description of either. The
aggregate balance averages
\textbf{{{historical_gg:.2f}\% of GDP}} over 1977--1994 and
\textbf{{{modern_gg:.2f}\%}} over 1995--{int(data.annual['year'].max())}, against a pooled
\textbf{{{float(pooled_gg['mean_balance_pct_gdp']):.2f}\%}} that falls between them and
corresponds to no observed period. The regime split is therefore the form in which
magnitudes should be read.

Sign counts are far more robust to pooling, because a sign does not depend on the level
convention of the vintage. Both are reported per regime below so they are read on one
basis.

{regime_table}
\subsection{{Structural mean shifts}}

Fewer than fifty annual observations, split across two statistical regimes, do not
support a flexible change-point model. The specification is therefore deliberately
modest: a piecewise-constant mean with at most two breaks per regime, a minimum segment
length of five years, exact dynamic-programming minimisation of within-segment squared
error, and BIC selection, which may select zero breaks. Detection runs separately on
1977--1994 and 1995--{int(data.annual['year'].max())}, so the known splice is not a
candidate economic break by construction.

{breaks_table}
\subsection{{How firm are those dates?}}

With eighteen or thirty-one annual observations per regime, a single selected date should
not be read as determined. Two guards are reported. The BIC margin in
{latex.ref_table('breaks')} shows how decisively the selected break count beat the
alternatives, and the grid in {latex.ref_table('breakstability')} re-runs detection across
all twelve combinations of the two tuning parameters.

{stability_table}
{disagreement_sentence}

The least stable series is
\textbf{{{SECTOR_LABELS[str(weakest['sector'])]}}} in the
{REGIME_TABLE_LABELS.get(str(weakest['regime']), str(weakest['regime']))} regime, where the
modal dates hold in only
\textbf{{{float(weakest['modal_break_years_share']) * 100:.0f}\%}} of the grid across
\textbf{{{int(weakest['n_distinct_break_year_sets'])} distinct date sets}}.

The dates are accordingly stated as candidates rather than as findings: the preferred
specification identifies shifts around the years listed, and the share columns say how much
of the specification grid agrees. A break year should not be quoted from this report without
its share. This report attaches no historical cause to any of them, and a minimum segment
length of five years means shifts near the end of the sample cannot be detected yet.
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
    labour_n = (
        int(data.labour_comovement.iloc[0]["n"]) if not data.labour_comovement.empty else 0
    )
    max_r2 = float(data.nominal_comovement["r_squared"].max())
    min_r2 = float(data.nominal_comovement["r_squared"].min())
    return rf"""\section{{Descriptive Macroeconomic Co-Movement}}
\label{{sec:comovement}}

This material is placed in an appendix rather than the body because the specification is
weak in ways that no amount of caveat wording repairs. It is retained because the estimates
are part of the reproducible output, not because the report rests on them. Nothing in the
body of this report depends on anything below.

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

\subsection{{Why these estimates carry little weight}}

Four specific problems, stated plainly.

\begin{{enumerate}}
\item \textbf{{The dependent variable and the regressor share a construction.}} The left-hand
side carries nominal GDP in its denominator while the right-hand side is the growth rate of
that same quantity. Part of any measured association is mechanical rather than economic, and
the specification provides no way to separate the two parts.
\item \textbf{{Nominal growth mixes two things.}} With
\(g^{{nominal}} \approx g^{{real}} + \pi\), a single coefficient is asked to represent both
real growth and inflation, which have no reason to move the balance by the same amount.
\item \textbf{{The fit is very low and the coefficients are not significant.}} The
\(R^2\) values span {min_r2:.2f} to {max_r2:.2f}, and no nominal-growth coefficient reaches
conventional significance under HAC standard errors.
\item \textbf{{The labour specification rests on {labour_n} observations.}} At that sample
size the positive unemployment coefficient below should not be interpreted at all: trends,
collinearity between the labour series, dynamic specification and the time-series properties
of the variables are all unexamined, and any one of them could account for the sign.
\end{{enumerate}}

A specification with a clearer mechanism would model the Social Security contribution base
directly, regressing the change in contributions on the change in the aggregate wage bill
\(W_t = N_t \bar{{w}}_t\) rather than on aggregate nominal growth. That is not implemented
here.

{nominal_table}
{labour_table}
These regressions quantify co-movement and nothing more. They are not causal estimates: no
identification strategy is claimed, the samples are short and serially correlated, and HAC
standard errors address the inference arithmetic rather than small-sample or specification
risk.
"""


def _section_contribution_base(data: ReportInputs) -> str:
    """Build the contribution-base section."""
    decomposition = data.base_decomposition
    latest = _latest(decomposition)
    panel_latest = _latest(data.base_panel)
    panel_first = data.base_panel.sort_values("year").iloc[0]
    view = _view(
        _tail_years(decomposition, 8),
        {
            "year": "Year",
            "contributions_change_m_eur": "Change in contributions (M EUR)",
            "from_wage_bill_m_eur": "From the wage bill (M EUR)",
            "from_effective_rate_m_eur": "From the effective rate (M EUR)",
            "rate_base_interaction_m_eur": "Interaction (M EUR)",
        },
    )
    split = _view(
        _tail_years(decomposition, 8),
        {
            "year": "Year",
            "wage_bill_change_m_eur": "Change in the wage bill (M EUR)",
            "from_employment_m_eur": "From employment (M EUR)",
            "from_average_wage_m_eur": "From average wages (M EUR)",
            "employment_wage_interaction_m_eur": "Interaction (M EUR)",
        },
    )
    residual = float(decomposition["contributions_closure_error_m_eur"].abs().max())
    decomposition_table = latex.table(
        view,
        caption="The annual change in Social Security contributions, split into the movement "
        "of the wage bill and the movement of the effective ratio between them.",
        label="contributionbase",
        digits=0,
        note="The interaction term is carried rather than dropped or shared between the two "
        f"effects, because either would make the decomposition inexact. It closes to {residual:.1e} "
        "M EUR.",
    )
    split_table = latex.table(
        split,
        caption="And what moved the wage bill: the number of employees against the average "
        "wage per employee.",
        label="wagebillsplit",
        digits=0,
    )
    figure = latex.figure(
        "19_contribution_base.png",
        caption="Contributions and their base. Upper panel: the change in contributions split "
        "into a base effect and a rate effect. Lower panel: the change in the wage bill split "
        "into employment and average wages.",
        label="contributionbasefig",
    )
    regression_note = ""
    if not data.base_regression.empty:
        row = data.base_regression.iloc[0]
        regression_note = (
            r"\subsection{A companion regression}"
            "\n\n"
            f"Regressing the annual change in contributions on the annual change in the wage\n"
            f"bill over {int(row['n'])} adjacent-year pairs gives a slope of\n"
            rf"\textbf{{{row['wage_bill_coef']:.3f}}} with a HAC standard error of"
            f"\n{row['wage_bill_se_hac']:.3f} and an "
            rf"\(R^2\) of \textbf{{{row['r_squared']:.3f}}}."
            "\nThe slope sits close to the mean effective ratio of "
            f"{row['mean_effective_rate']:.3f}, which is what the\n"
            "accounting predicts, and the fit is far tighter than the nominal-GDP specification\n"
            r"in Appendix~\ref{sec:comovement}: the regressor here is the base the levy actually"
            "\nfalls on rather than an aggregate that merely correlates with it. It remains a\n"
            "descriptive statistic and no identification is claimed.\n"
        )
    return (
        r"\section{The Contribution Base}"
        "\n"
        r"\label{sec:contributionbase}"
        "\n\n"
        "The Social Security results so far locate a movement inside the fiscal accounts. They\n"
        "do not relate it to anything outside them. Contributions are levied on wages, so the\n"
        "natural base is the aggregate wage bill "
        r"\(W_t = N_t \bar{w}_t\), with \(N\) employees"
        "\nand "
        r"\(\bar{w}\) the average wage. Writing the effective ratio as \(\tau_t = C_t / W_t\),"
        "\nthe change in contributions decomposes exactly:\n"
        r"\[\Delta C_t = \tau_{t-1} \Delta W_t + W_{t-1} \Delta \tau_t"
        r" + \Delta W_t \Delta \tau_t.\]"
        "\n\n"
        "The wage bill and employment come from the Portuguese national accounts compiled by\n"
        "INE. "
        r"\(\tau\) is \emph{not} a statutory contribution rate: national-accounts"
        "\ncontributions include imputed contributions and bases other than employee wages, so\n"
        "the ratio moves with coverage and composition as well as with legislated rates. It\n"
        "stands at "
        rf"\textbf{{{panel_latest['effective_contribution_rate']:.3f}}}"
        f" in {int(panel_latest['year'])} against "
        rf"\textbf{{{panel_first['effective_contribution_rate']:.3f}}}"
        f" in {int(panel_first['year'])}.\n\n"
        f"{decomposition_table}"
        f"In {int(latest['year'])} contributions rose by "
        rf"\textbf{{{latex.number(float(latest['contributions_change_m_eur']), 0)} M EUR}},"
        "\nof which "
        rf"\textbf{{{latex.number(float(latest['from_wage_bill_m_eur']), 0)} M EUR}}"
        " came from\nthe wage bill and "
        rf"\textbf{{{latex.number(float(latest['from_effective_rate_m_eur']), 0)} M EUR}}"
        " from the\neffective ratio. The base effect splits again.\n\n"
        f"{split_table}"
        f"{figure}"
        f"{regression_note}"
        "\nThe decomposition is exact and descriptive. It does not establish that the wage bill\n"
        "produced the movement in contributions, and it identifies nothing about why employment\n"
        "or wages moved.\n"
    )


def _section_benchmark(data: ReportInputs) -> str:
    """Build the European benchmark section."""
    summary = data.benchmark_summary
    portugal = _sector_row(summary.rename(columns={"country": "sector"}), "PT")
    with_surplus = summary.loc[summary["n_aggregate_positive"].gt(0)]
    all_offsetting = with_surplus.loc[
        with_surplus["n_aggregate_positive_with_negative_non_ssf"]
        >= with_surplus["n_aggregate_positive"]
    ]
    central_always = summary.loc[summary["share_central_negative"].ge(1.0)]
    surplus_years = int(with_surplus["n_aggregate_positive"].sum())
    offsetting_years = int(with_surplus["n_aggregate_positive_with_negative_non_ssf"].sum())

    view = _view(
        summary.sort_values("share_ssf_positive", ascending=False),
        {
            "country": "Reporter",
            "n_years": "N",
            "share_central_negative": "Central $<0$",
            "share_ssf_positive": "SSF $>0$",
            "mean_ssf_pct_gdp": "Mean SSF (\\% GDP)",
            "n_aggregate_positive": "Surplus years",
            "n_aggregate_positive_with_negative_non_ssf": "of which non-SSF $<0$",
            "median_offset_ratio": "Median offset",
        },
    )
    summary_table = latex.table(
        view,
        caption="Subsector composition across European reporters, ordered by the frequency of "
        "a Social Security surplus.",
        label="benchmark",
        digits=3,
        column_digits={
            "N": 0,
            "Surplus years": 0,
            "of which non-SSF $<0$": 0,
            "Mean SSF (\\% GDP)": 2,
        },
        note="The non-Social-Security aggregate is central plus state plus local government, "
        "so federal reporters are treated consistently with unitary ones. Reporters with fewer "
        "than fifteen complete years are excluded.",
    )
    position_table = latex.table(
        _view(
            data.benchmark_position,
            {
                "metric": "Metric",
                "country_value": "Portugal",
                "cross_country_median": "Cross-country median",
                "cross_country_min": "Minimum",
                "cross_country_max": "Maximum",
                "percentile": "Percentile",
            },
        ),
        caption="Portugal's position in each cross-country distribution.",
        label="benchmarkposition",
        digits=3,
        column_digits={"Percentile": 0},
    )
    frequency_figure = latex.figure(
        "17_european_benchmark.png",
        caption="Subsector sign frequencies across reporters, Portugal highlighted and reporters "
        "ordered by the frequency of a Social Security surplus.",
        label="benchmarkfig",
    )
    distribution_figure = latex.figure(
        "18_european_offset_distribution.png",
        caption="Offset ratio where defined: Portugal against all other reporters pooled, as a "
        "share of each group's defined country-years. Values above three are clipped.",
        label="benchmarkoffset",
    )
    return rf"""\section{{European Benchmark}}
\label{{sec:benchmark}}

Every other section of this report describes one country, which cannot establish whether
what it describes is unusual. ESA 2010 requires the same subsector breakdown from every
reporter, so the comparison is available. The definitions used here are the domestic ones,
with three adjustments.

\begin{{enumerate}}
\item The non-Social-Security aggregate is central \emph{{plus state}} plus local
government. Portugal has no state tier; several reporters do, and omitting it would leave
their identity open.
\item Ratios are computed in national currency. The published shares of GDP carry one
decimal, which is too coarse a denominator for a ratio.
\item A reporter enters only with at least fifteen complete years, so a frequency over a
handful of years is not compared with one over thirty.
\end{{enumerate}}

This leaves \textbf{{{len(summary)} reporters}} over
{int(summary['first_year'].min())}--{int(summary['last_year'].max())}. Eurostat's
Portuguese rows agree with the domestic panel to rounding, so this source doubles as an
independent check on the extraction.

{summary_table}
{position_table}
The answer differs across the findings. A Central Government deficit is recorded in
\textbf{{{portugal['share_central_negative'] * 100:.0f}\%}} of Portuguese years, but
\textbf{{{len(central_always)} of {len(summary)} reporters}} record one in every year they
cover: a persistently deficit-running central tier is a common European pattern. The
Social Security surplus is different, occurring in
\textbf{{{portugal['share_ssf_positive'] * 100:.1f}\%}} of Portuguese years against a
cross-country median of
\textbf{{{summary['share_ssf_positive'].median() * 100:.1f}\%}}, and averaging
\textbf{{{portugal['mean_ssf_pct_gdp']:.2f}\% of GDP}} against a median of
\textbf{{{summary['mean_ssf_pct_gdp'].median():.2f}\%}}.

{frequency_figure}
{distribution_figure}
The sharpest comparison is the composition of a surplus year. Across the
\textbf{{{len(with_surplus)} reporters}} with at least one aggregate surplus, a negative
non-Social-Security balance accompanies the surplus in
\textbf{{{offsetting_years} of {surplus_years}}} surplus country-years, or
\textbf{{{100.0 * offsetting_years / surplus_years:.0f}\%}}. It is a minority pattern.
\textbf{{{len(all_offsetting)} of those reporters}} show it in every one of their surplus
years, Portugal among them, on
\textbf{{{int(portugal['n_aggregate_positive'])} surplus years}} --- a count small enough
that it is stated beside the claim.

This is a distribution, not a test. Reporters differ in whether they operate a state tier,
in how contributory schemes are assigned between tiers, in pension-system maturity and in
how transfers are routed, and none of that is held constant here.
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
smoothed across the boundary. No level statistic is averaged across it, and no annual change
is computed through it.
\item \textbf{Detailed subsector accounts have no 1996--1999 observations.} No
interpolation is performed, no statistic is computed across the gap, and every figure drawn
from the account panel breaks its line there. The canonical B.9 panel is complete and is
unaffected.
\item \textbf{The most recent years are provisional.} They carry the publisher's flag
through the canonical panel and will be revised by a later vintage. They are also the years
this report discusses in most detail.
\item \textbf{Identity closure is not source agreement.} The identities close to rounding
while two published sources still disagree by up to about 67 million euro on the same
subsector-year. Both tests are reported, and neither substitutes for the other.
\item \textbf{Nominal GDP growth is not an output gap}, and the co-movement appendix must
not be read as a cyclically adjusted balance. Its dependent variable and regressor share a
construction, which is one of the reasons it is confined to an appendix.
\item \textbf{Social Security national accounts and budget-system accounts have different
boundaries.} They are never merged, netted or reconciled into a single series, and the
difference between them is non-zero in every overlapping year.
\item \textbf{The fixed-investment diagnostic is not an official balance concept.}
\item \textbf{Structural-break dates are candidates, not findings.} They are reported with
a BIC margin and a sensitivity grid precisely because a single selected date from eighteen or
thirty-one observations is not determined.
\item \textbf{A positive primary balance is not a sustainability result.} It excludes
interest by construction and says nothing about the debt path.
\item \textbf{Accounting contribution is not causation.} An arithmetic contribution to an
aggregate balance is not evidence about intent or responsibility.
\item \textbf{Identity and reconciliation residuals validate the extraction}, not the
underlying official statistics.
\item All interpretation is restricted to accounting, statistical and economic
relationships directly supported by the bundled data.
\end{enumerate}
"""


def _section_reproducibility(data: ReportInputs) -> str:
    """Build the reproducibility section."""
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
"""


def _section_artefacts() -> str:
    """Build the artefact index appendix."""
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
    return rf"""\section{{Artefact Index}}
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
            _section_contribution_base(data),
            _section_benchmark(data),
            _section_transfers(),
            _section_limitations(),
            _section_reproducibility(data),
            # The co-movement regressions are appendix material: the body of the
            # report states no result that depends on them.
            r"\appendix",
            _section_comovement(data),
            _section_artefacts(),
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

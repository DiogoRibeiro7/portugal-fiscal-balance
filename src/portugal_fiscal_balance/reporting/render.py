"""Render the final English report from persisted CSV/JSON outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _fmt(value: object, digits: int = 2) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def _markdown_table(frame: pd.DataFrame, digits: int = 2) -> str:
    columns = list(frame.columns)
    header = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = [
        "| " + " | ".join(_fmt(value, digits) for value in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    ]
    return "\n".join([header, rule, *rows])


def render_report(root: Path) -> Path:
    """Generate report/report.md using only outputs already written by the pipeline."""
    tables = root / "outputs" / "tables"
    metrics_dir = root / "outputs" / "metrics"
    report_dir = root / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    summary = json.loads((metrics_dir / "analysis_summary.json").read_text(encoding="utf-8"))
    annual = pd.read_csv(root / "data" / "processed" / "annual_balance_metrics_1977_2025.csv")
    accounts = pd.read_csv(root / "data" / "processed" / "subsector_accounts_1977_2025.csv")
    persistence = pd.read_csv(tables / "persistence_summary.csv")
    breaks = pd.read_csv(tables / "structural_breaks.csv")
    primary = pd.read_csv(tables / "primary_balance_and_interest.csv")
    investment = pd.read_csv(tables / "investment_diagnostic.csv")
    debt = pd.read_csv(tables / "debt_stock_flow_reconciliation.csv")
    ssf = pd.read_csv(tables / "social_security_account_metrics.csv")
    ss_systems = pd.read_csv(tables / "social_security_system_metrics_2019_2025.csv")
    ss_detail = pd.read_csv(tables / "social_security_detail_metrics_2024_2025.csv")
    nominal_comovement = pd.read_csv(tables / "nominal_gdp_balance_comovement.csv")
    labour_comovement = pd.read_csv(tables / "historical_ssf_labour_comovement.csv")

    positive_years = summary["balance_summary"]["positive_aggregate_balance_years"]
    latest = annual.loc[annual["year"].eq(2025)].iloc[0]
    selected_recent = annual.loc[annual["year"].isin(positive_years), [
        "year",
        "general_government_balance_m_eur",
        "central_government_balance_m_eur",
        "regional_local_balance_m_eur",
        "social_security_balance_m_eur",
        "non_ssf_balance_m_eur",
        "ssf_offset_ratio",
    ]].copy()
    selected_recent.columns = [
        "Year",
        "GG balance (M€)",
        "Central (M€)",
        "Regional/local (M€)",
        "SSF (M€)",
        "Non-SSF (M€)",
        "SSF offset ratio",
    ]

    persistence_view = persistence.copy()
    persistence_view.columns = [
        "Sector",
        "N",
        "Positive years",
        "Negative years",
        "Mean (% GDP)",
        "Median (% GDP)",
        "Longest positive run",
        "Longest negative run",
    ]

    central_2025 = primary.loc[(primary["sector"] == "central_government") & (primary["year"] == 2025)].iloc[0]
    invest_2025 = investment.loc[(investment["sector"] == "central_government") & (investment["year"] == 2025)].iloc[0]
    debt_2025 = debt.loc[(debt["sector"] == "general_government") & (debt["year"] == 2025)].iloc[0]
    ssf_2025 = ssf.loc[ssf["year"].eq(2025)].iloc[0]
    systems_2025 = ss_systems.loc[ss_systems["year"].eq(2025)].iloc[0]
    detail_2025 = ss_detail.loc[ss_detail["year"].eq(2025)].iloc[0]

    coverage = accounts.groupby("sector")["year"].agg(["min", "max", "count"]).reset_index()
    coverage.columns = ["Sector", "First year", "Last year", "Observations"]

    report = fr"""# Portugal's General-Government Balance by Subsector, 1977–2025

## Abstract

This report decomposes Portugal's annual general-government net lending (+) / net borrowing (-) into Central Government, Regional and Local Government, and Social Security Funds (SSF). The analysis is empirical and accounting-focused. It studies long-run balance composition, year-to-year attribution, revenue and expenditure dynamics, persistence, structural mean shifts, Social Security revenue composition, primary balances, public investment, debt-flow reconciliation, and descriptive macroeconomic co-movement.

The central accounting identity is

\[
B^{{GG}}_t = B^{{C}}_t + B^{{RL}}_t + B^{{SSF}}_t.
\]

No causal, normative, or policy-intent interpretation is assigned to this identity.

## 1. Data and reproducibility

The balance panel covers **1977–2025**, or **49 annual observations**. Historical data come from the Banco de Portugal / INE long series. The continuous modern balance bridge uses INE data distributed through PORDATA, while the CFP ESA 2010 workbooks provide modern revenue, expenditure, interest, investment, debt and stock-flow data.

The known statistical splice at **1995** is retained explicitly. No smoothing is applied across it. Detailed subsector revenue/expenditure accounts are available for 1977–1995 in the historical source and 2000–2025 in the modern CFP source; **1996–1999 are therefore left missing rather than imputed**.

{_markdown_table(coverage, 0)}

The maximum absolute subsector closure error in the canonical balance panel is **{summary['balance_validation']['max_abs_closure_error_m_eur']:.2f} M€**. The maximum revenue-minus-expenditure account identity error is **{summary['max_abs_account_identity_error_m_eur']:.6f} M€**. The modern debt-flow reconciliation closes with a maximum absolute error of **{summary['max_abs_debt_reconciliation_error_m_eur']:.6f} M€**.

## 2. Long-run subsector decomposition

![Long-run balances](../outputs/figures/01_long_run_balances.png)

Across the full 1977–2025 balance panel, the aggregate General Government balance is positive in **{len(positive_years)} years: {', '.join(str(v) for v in positive_years)}**. The table below reports sign persistence and balance magnitudes by subsector.

{_markdown_table(persistence_view, 3)}

The Central Government balance is negative in **{int(persistence.loc[persistence['sector'].eq('central_government'), 'negative_years'].iloc[0])} of 49 observations** in the canonical balance series. By contrast, SSF has a positive balance in **{int(persistence.loc[persistence['sector'].eq('social_security_funds'), 'positive_years'].iloc[0])} observations**. These are descriptive frequencies, not counterfactual statements about what the aggregate balance would have been under a different institutional arrangement.

### Positive aggregate-balance years

{_markdown_table(selected_recent, 3)}

In 2025, the identity is

\[
{latest['general_government_balance_m_eur']:.0f}
=
{latest['central_government_balance_m_eur']:.0f}
+
{latest['regional_local_balance_m_eur']:.0f}
+
{latest['social_security_balance_m_eur']:.0f}
\quad \text{{M€}}.
\]

The combined non-SSF balance is **{latest['non_ssf_balance_m_eur']:.0f} M€**, while the SSF offset ratio is **{latest['ssf_offset_ratio']:.3f}**. The ratio is defined as SSF balance divided by the absolute value of the negative non-SSF balance whenever those signs make the ratio meaningful.

![SSF offset ratio](../outputs/figures/02_ssf_offset_ratio.png)

## 3. Year-to-year attribution

The annual change in the aggregate balance can be written exactly as

\[
\Delta B^{{GG}}_t
=
\Delta B^{{C}}_t
+
\Delta B^{{RL}}_t
+
\Delta B^{{SSF}}_t.
\]

The repository stores this decomposition for every adjacent year in `outputs/tables/balance_change_attribution.csv`. This distinguishes the level of a subsector balance from its contribution to an annual improvement or deterioration.

![Annual balance changes](../outputs/figures/03_balance_change_attribution.png)

## 4. Revenue and expenditure dynamics

For every sector-year with detailed accounts, the balance is decomposed as

\[
B_{{i,t}} = R_{{i,t}} - E_{{i,t}},
\]

and therefore

\[
\Delta B_{{i,t}} = \Delta R_{{i,t}} - \Delta E_{{i,t}}.
\]

The exact annual decomposition is stored in `outputs/tables/revenue_expenditure_change_decomposition.csv`. Source gaps are not bridged when calculating changes.

![Central Government revenue and expenditure](../outputs/figures/04_central_revenue_expenditure.png)

## 5. Social Security Funds: revenue composition and internal systems

The long-run SSF account series contains total revenue, total expenditure and social contributions. In 2025, social contributions were **{ssf_2025['contributions_share_total_revenue'] * 100:.2f}% of total SSF revenue** in the ESA 2010 account table.

![Social Security contribution share](../outputs/figures/05_ssf_contribution_share.png)

The CFP's separate Social Security budget tables provide a second, non-interchangeable view of the system. In 2025, the reported internal balances were:

- Previdential system: **{systems_2025['previdential_system_balance_m_eur']:.0f} M€**;
- Social Protection of Citizenship system: **{systems_2025['citizenship_system_balance_m_eur']:.0f} M€**;
- Special regimes: **{systems_2025['special_regimes_balance_m_eur']:.0f} M€**.

For the detailed 2025 budget table, previdential contributions account for **{detail_2025['previdential_contribution_share_revenue'] * 100:.2f}%** of previdential revenue. These budget-system figures are analysed separately from the national-accounts SSF balance because the accounting boundaries differ.

## 6. Primary balance and interest

The primary balance is reconstructed as

\[
PB_{{i,t}} = B_{{i,t}} + I_{{i,t}},
\]

where \(I\) is interest expenditure. For Central Government in 2025, the headline balance was **{central_2025['balance_m_eur']:.0f} M€**, interest expenditure was **{central_2025['interest_m_eur']:.0f} M€**, and the recomputed primary balance was **{central_2025['primary_balance_recomputed_m_eur']:.0f} M€**.

![Central primary balance](../outputs/figures/06_central_primary_balance.png)

This decomposition isolates the accounting contribution of interest from the remainder of the balance. It is used only to separate interest expenditure from the remaining accounting balance.

## 7. Fixed-capital formation diagnostic

The repository reports an explicitly non-official diagnostic

\[
B^{{before\ GFCF}}_{{i,t}} = B_{{i,t}} + GFCF_{{i,t}}.
\]

For Central Government in 2025, GFCF was **{invest_2025['gfcf_m_eur']:.0f} M€**, and the analytical balance before GFCF was **{invest_2025['balance_before_gfcf_m_eur']:.0f} M€**. This does not redefine the official fiscal balance; it only quantifies the scale of fixed-capital formation relative to B.9.

## 8. Debt and stock-flow adjustment

Debt dynamics need not equal minus the annual B.9 balance. The modern CFP tables allow the reconciliation

\[
\Delta Debt_t = -B_t + SFA_t,
\]

where \(SFA\) is the stock-flow adjustment. In 2025, General Government Maastricht debt was **{debt_2025['debt_pct_gdp']:.2f}% of GDP**, and the stock-flow adjustment was **{debt_2025['stock_flow_adjustment_pct_gdp']:.2f}% of GDP**.

![Debt and stock-flow adjustment](../outputs/figures/07_general_government_debt.png)

## 9. Persistence and structural mean shifts

Structural mean-shift detection is performed separately inside the 1977–1994 historical regime and the 1995–2025 modern regime. This prevents the known 1995 statistical splice from being mistaken for an economic break. A conservative piecewise-constant model with at most two breaks and a minimum five-year segment is selected by BIC.

{_markdown_table(breaks[['regime', 'sector', 'n_breaks', 'break_years', 'segment_means_pct_gdp']], 3)}

The detected dates are descriptive model outputs. The repository does not assign historical causes to them automatically.

## 10. Descriptive macroeconomic co-movement

The full-period macroeconomic regression uses **nominal GDP growth**, because that variable can be reconstructed consistently from the bundled sources across 1977–2025. It is deliberately not described as an output gap or as a structural cyclical adjustment. HAC standard errors are used.

{_markdown_table(nominal_comovement, 4)}

For 1978–1995 only, the historical Banco de Portugal / INE workbook also permits a small SSF model using employment growth and the unemployment rate:

{_markdown_table(labour_comovement, 4) if not labour_comovement.empty else 'Insufficient historical labour observations.'}

These regressions quantify co-movement. They are not causal estimates.

## 11. Intergovernmental transfers

Historical source tables identify current and capital transfers received and paid between public administrations. The repository computes a mechanical transfer-reallocation sensitivity:

\[
B^{{sens}}_{{i,t}} = B_{{i,t}} - (T^{{received}}_{{i,t}} - T^{{paid}}_{{i,t}}).
\]

This is intentionally not labelled an underlying or true balance. Removing a transfer while leaving the associated expenditure responsibility unchanged would generally not define a meaningful counterfactual.

## 12. Methodological limitations

1. **1995 is a known source/methodology splice.** Both historical and modern 1995 values are retained in `data/interim/methodology_overlap_1995.csv`.
2. **Detailed subsector accounts have a 1996–1999 gap.** No interpolation is performed.
3. **Nominal GDP growth is not an output gap.** The full-period co-movement analysis should not be read as a cyclically adjusted balance.
4. **Social Security national accounts and budget-system accounts have different boundaries.** They are never merged into one balance series.
5. **The fixed-investment diagnostic is not an official balance concept.**
6. **Structural-break dates are statistical summaries, not causal event labels.**
7. **All interpretation is restricted to accounting, statistical and economic relationships directly supported by the data.**

## 13. Reproducibility

The repository preserves raw source workbooks, source-specific intermediate CSVs, canonical processed datasets, analysis tables, figures, executed notebooks and SHA-256 hashes of every bundled raw file. The default execution is:

```bash
poetry install
make all
```

The final report is regenerated from persisted analysis outputs rather than from hard-coded conclusions.
"""

    output = report_dir / "report.md"
    output.write_text(report, encoding="utf-8")
    return output

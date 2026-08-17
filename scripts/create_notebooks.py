#!/usr/bin/env python
"""Create the repository's notebook narratives."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"
NB.mkdir(parents=True, exist_ok=True)

SETUP = """from pathlib import Path
import sys
import pandas as pd
from IPython.display import display

ROOT = Path.cwd()
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
pd.set_option('display.max_columns', 100)
"""


def notebook(name: str, title: str, intro: str, cells: list[tuple[str, str]]) -> None:
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python", "version": "3"}
    built = [nbf.v4.new_markdown_cell(f"# {title}\n\n{intro}"), nbf.v4.new_code_cell(SETUP)]
    for kind, content in cells:
        built.append(nbf.v4.new_markdown_cell(content) if kind == "md" else nbf.v4.new_code_cell(content))
    nb.cells = built
    nbf.write(nb, NB / name)


notebook(
    "00_research_protocol.ipynb",
    "Research protocol",
    "This notebook fixes the accounting objects, source regimes and non-interpretive scope before any results are inspected.",
    [
        ("md", "## Accounting identity\n\n$B^{GG}_t=B^{C}_t+B^{RL}_t+B^{SSF}_t$. The study describes accounting contributions, temporal dynamics and statistical relationships. It does not infer intent or assign normative labels."),
        ("code", "import yaml\nconfig = yaml.safe_load((ROOT / 'config' / 'sources.yml').read_text())\ndisplay(pd.DataFrame(config['sources']).T[['institution','coverage','local_file']])"),
        ("md", "## Reproducibility rules\n\nRaw files are retained; extracted tables go to `data/interim`; canonical panels go to `data/processed`; calculated tables and metrics go to `outputs`; the report is generated from those persisted results."),
    ],
)

notebook(
    "01_extract_historical_data.ipynb",
    "Historical extraction: Banco de Portugal / INE",
    "Extract the 1977–1995 historical balance, account, transfer and macro tables directly from the bundled official workbook.",
    [
        ("code", "from portugal_fiscal_balance.sources.banco_portugal import extract_long_series\nfrom portugal_fiscal_balance.io import write_csv\nfrom portugal_fiscal_balance.paths import RAW, INTERIM\nh = extract_long_series(RAW / 'banco_portugal' / 'series_longas_2023-12.xlsx')\nwrite_csv(h.balances, INTERIM / 'historical_balances_1977_1995.csv')\nwrite_csv(h.accounts, INTERIM / 'historical_accounts_1977_1995.csv')\nwrite_csv(h.transfers, INTERIM / 'historical_intragov_transfers_1977_1995.csv')\nwrite_csv(h.macro, INTERIM / 'historical_macro_1977_1995.csv')\nprint({'balances': h.balances.shape, 'accounts': h.accounts.shape, 'transfers': h.transfers.shape, 'macro': h.macro.shape})"),
        ("code", "display(h.accounts.loc[h.accounts['year'].ge(1990), ['year','sector','total_revenue_m_eur','total_expenditure_m_eur','interest_m_eur','gfcf_m_eur','balance_m_eur']].head(16))"),
        ("code", "display(h.accounts.groupby('sector')['account_identity_error_m_eur'].apply(lambda x: x.abs().max()).rename('max_abs_identity_error_m_eur').to_frame())"),
    ],
)

notebook(
    "02_extract_modern_data.ipynb",
    "Modern extraction: INE/PORDATA and CFP",
    "Load the continuous modern B.9 bridge and independently parse the CFP ESA 2010 account and debt workbooks.",
    [
        ("code", "from portugal_fiscal_balance.sources.pordata import load_balance_snapshot\nfrom portugal_fiscal_balance.sources.cfp import extract_cfp_annual, extract_social_security_detail\nfrom portugal_fiscal_balance.paths import RAW\nmodern = load_balance_snapshot(RAW / 'pordata' / 'pordata_2785_balance_by_level_1995_2025.csv')\ncfp = extract_cfp_annual(RAW / 'cfp' / 'cfp_sec2010_annual_general_government_2026-04-15.xlsx', RAW / 'cfp' / 'cfp_sec2010_annual_subsectors_2026-04-15.xlsx')\nss_systems, ss_detail = extract_social_security_detail(RAW / 'cfp' / 'cfp_rel_04_2026_social_security_underlying_data.xlsx')\nprint({'balance_bridge': modern.shape, 'cfp_accounts': cfp.accounts.shape, 'cfp_debt': cfp.debt.shape})"),
        ("code", "display(modern.tail(8))"),
        ("code", "display(cfp.accounts.groupby('sector')['year'].agg(['min','max','count']))"),
        ("code", "display(ss_detail)"),
    ],
)

notebook(
    "03_harmonize_and_validate.ipynb",
    "Harmonisation and validation",
    "Construct the canonical 1977–2025 B.9 panel, retain the 1995 overlap, and expose the four-year detailed-account gap rather than imputing it.",
    [
        ("code", "from portugal_fiscal_balance.sources.banco_portugal import extract_long_series\nfrom portugal_fiscal_balance.sources.pordata import load_balance_snapshot\nfrom portugal_fiscal_balance.sources.cfp import extract_cfp_annual\nfrom portugal_fiscal_balance.processing.harmonize import harmonize_balance_panel, harmonize_account_panel, build_methodology_overlap\nfrom portugal_fiscal_balance.processing.validation import validate_balance_panel, validate_accounts\nfrom portugal_fiscal_balance.paths import RAW\nh = extract_long_series(RAW / 'banco_portugal' / 'series_longas_2023-12.xlsx')\nm = load_balance_snapshot(RAW / 'pordata' / 'pordata_2785_balance_by_level_1995_2025.csv')\nc = extract_cfp_annual(RAW / 'cfp' / 'cfp_sec2010_annual_general_government_2026-04-15.xlsx', RAW / 'cfp' / 'cfp_sec2010_annual_subsectors_2026-04-15.xlsx')\npanel = harmonize_balance_panel(h.balances, m, c.general_government[['year','nominal_gdp_m_eur']])\naccounts = harmonize_account_panel(h.accounts, c.accounts)\nprint(validate_balance_panel(panel))\ndisplay(build_methodology_overlap(h.balances, m))"),
        ("code", "display(accounts.groupby('sector')['year'].agg(['min','max','count']))\ndisplay(validate_accounts(accounts).groupby('sector')['identity_error_m_eur'].apply(lambda x: x.abs().max()).to_frame())"),
    ],
)

notebook(
    "04_balance_decomposition.ipynb",
    "Long-run balance decomposition",
    "Inspect the canonical B.9 decomposition and neutral SSF offset metrics.",
    [
        ("code", "annual = pd.read_csv(ROOT / 'data' / 'processed' / 'annual_balance_metrics_1977_2025.csv')\ndisplay(annual.tail(10)[['year','general_government_balance_m_eur','central_government_balance_m_eur','regional_local_balance_m_eur','social_security_balance_m_eur','non_ssf_balance_m_eur','ssf_offset_ratio']])"),
        ("code", "positive = annual.loc[annual['aggregate_balance_positive'], ['year','general_government_balance_m_eur','non_ssf_balance_m_eur','social_security_balance_m_eur','ssf_offset_ratio']]\ndisplay(positive)"),
        ("md", "The offset ratio is defined only when the non-SSF balance is negative and the SSF balance is positive. It is an accounting ratio, not a counterfactual."),
    ],
)

notebook(
    "05_revenue_expenditure.ipynb",
    "Revenue and expenditure decomposition",
    "Move from B.9 levels to the exact identity $B=R-E$ and its adjacent-year change decomposition.",
    [
        ("code", "accounts = pd.read_csv(ROOT / 'data' / 'processed' / 'subsector_accounts_1977_2025.csv')\nchanges = pd.read_csv(ROOT / 'outputs' / 'tables' / 'revenue_expenditure_change_decomposition.csv')\ndisplay(accounts.loc[(accounts['sector']=='central_government') & accounts['year'].ge(2015), ['year','total_revenue_pct_gdp','total_expenditure_pct_gdp','balance_pct_gdp','interest_pct_gdp','gfcf_pct_gdp']])"),
        ("code", "display(changes.loc[(changes['sector']=='social_security_funds') & changes['year'].ge(2018)].tail(10))"),
        ("code", "print('Maximum decomposition residual (M€):', changes['decomposition_error_m_eur'].abs().max())"),
    ],
)

notebook(
    "06_year_to_year_attribution.ipynb",
    "Year-to-year balance attribution",
    "Attribute every annual change in General Government B.9 to changes in the three subsectors.",
    [
        ("code", "changes = pd.read_csv(ROOT / 'outputs' / 'tables' / 'balance_change_attribution.csv')\ndisplay(changes.tail(12)[['year','aggregate_change_m_eur','central_change_m_eur','regional_local_change_m_eur','ssf_change_m_eur','change_closure_error_m_eur']])"),
        ("code", "print('Maximum absolute change-identity residual (M€):', changes['change_closure_error_m_eur'].abs().max())"),
    ],
)

notebook(
    "07_persistence.ipynb",
    "Balance persistence and sign transitions",
    "Quantify how often each subsector is positive or negative, longest runs, and empirical one-year transition probabilities.",
    [
        ("code", "persistence = pd.read_csv(ROOT / 'outputs' / 'tables' / 'persistence_summary.csv')\ntransitions = pd.read_csv(ROOT / 'outputs' / 'tables' / 'transition_probabilities.csv')\ndisplay(persistence)"),
        ("code", "display(transitions.sort_values(['sector','state','next_state']))"),
    ],
)

notebook(
    "08_structural_breaks.ipynb",
    "Structural mean shifts",
    "Detect conservative piecewise-constant mean shifts separately inside the historical and modern statistical regimes.",
    [
        ("code", "breaks = pd.read_csv(ROOT / 'outputs' / 'tables' / 'structural_breaks.csv')\ndisplay(breaks)"),
        ("md", "Break dates are statistical outputs. The notebook does not attach historical causes automatically. The known 1995 splice is excluded by fitting the two regimes separately."),
    ],
)

notebook(
    "09_social_security_mechanisms.ipynb",
    "Social Security Funds mechanisms",
    "Analyse SSF total revenue, expenditure, social contributions and the separate CFP internal system tables without merging incompatible accounting boundaries.",
    [
        ("code", "ssf = pd.read_csv(ROOT / 'outputs' / 'tables' / 'social_security_account_metrics.csv')\nsystems = pd.read_csv(ROOT / 'outputs' / 'tables' / 'social_security_system_metrics_2019_2025.csv')\ndetail = pd.read_csv(ROOT / 'outputs' / 'tables' / 'social_security_detail_metrics_2024_2025.csv')\ndisplay(ssf.tail(12)[['year','total_revenue_m_eur','social_contributions_m_eur','contributions_share_total_revenue','total_expenditure_m_eur','balance_m_eur']])"),
        ("code", "display(systems)\ndisplay(detail)"),
    ],
)

notebook(
    "10_intergovernmental_transfers.ipynb",
    "Intergovernmental transfer sensitivity",
    "Inspect a purely mechanical removal of historical net transfers. This is a sensitivity of balance location, not an alternative underlying balance.",
    [
        ("code", "sensitivity = pd.read_csv(ROOT / 'outputs' / 'tables' / 'historical_transfer_reallocation_sensitivity.csv')\ndisplay(sensitivity.loc[sensitivity['year'].ge(1988)].tail(18))"),
        ("md", "A transfer may finance an expenditure responsibility assigned to the recipient. The sensitivity therefore cannot be read as the balance that would prevail if the transfer did not exist."),
    ],
)

notebook(
    "11_primary_balance.ipynb",
    "Primary balance and interest",
    "Separate interest expenditure from B.9 and verify the primary-balance identity.",
    [
        ("code", "primary = pd.read_csv(ROOT / 'outputs' / 'tables' / 'primary_balance_and_interest.csv')\ndisplay(primary.loc[(primary['sector']=='central_government') & primary['year'].ge(2015), ['year','balance_m_eur','interest_m_eur','primary_balance_recomputed_m_eur','primary_balance_identity_error_m_eur']])"),
        ("code", "print('Maximum absolute primary-balance identity error (M€):', primary['primary_balance_identity_error_m_eur'].abs().max())"),
    ],
)

notebook(
    "12_investment_diagnostic.ipynb",
    "Fixed-capital-formation diagnostic",
    "Quantify GFCF relative to B.9 using the explicitly non-official diagnostic $B^{before\\ GFCF}=B+GFCF$.",
    [
        ("code", "investment = pd.read_csv(ROOT / 'outputs' / 'tables' / 'investment_diagnostic.csv')\ndisplay(investment.loc[(investment['sector']=='central_government') & investment['year'].ge(2015), ['year','balance_m_eur','gfcf_m_eur','balance_before_gfcf_m_eur','gfcf_pct_gdp']])"),
    ],
)

notebook(
    "13_debt_reconciliation.ipynb",
    "Debt and stock-flow reconciliation",
    "Reconcile modern Maastricht debt changes with B.9 and the stock-flow adjustment.",
    [
        ("code", "debt = pd.read_csv(ROOT / 'outputs' / 'tables' / 'debt_stock_flow_reconciliation.csv')\ndisplay(debt.loc[(debt['sector']=='general_government') & debt['year'].ge(2010), ['year','balance_m_eur','debt_change_m_eur','stock_flow_adjustment_m_eur','debt_pct_gdp','reconciliation_error_m_eur']])"),
        ("code", "print('Maximum absolute reconciliation residual (M€):', debt['reconciliation_error_m_eur'].abs().max())"),
    ],
)

notebook(
    "14_macroeconomic_comovement.ipynb",
    "Descriptive macroeconomic co-movement",
    "Estimate transparent HAC regressions using nominal GDP growth for the full period and historical labour controls where the bundled long series permit it.",
    [
        ("code", "nominal = pd.read_csv(ROOT / 'outputs' / 'tables' / 'nominal_gdp_balance_comovement.csv')\nlabour = pd.read_csv(ROOT / 'outputs' / 'tables' / 'historical_ssf_labour_comovement.csv')\ndisplay(nominal)"),
        ("code", "display(labour)"),
        ("md", "Nominal GDP growth is not an output gap. These regressions are descriptive co-movement estimates and are not used as causal or structural fiscal models."),
    ],
)

notebook(
    "15_build_report.ipynb",
    "Build the final report",
    "Regenerate the English LaTeX report strictly from persisted pipeline outputs.",
    [
        ("code", "from portugal_fiscal_balance.reporting.render import render_report\npath = render_report(ROOT)\nprint(path)"),
        ("code", "text = (ROOT / 'report' / 'report.tex').read_text(encoding='utf-8')\nprint(text[:5000])"),
    ],
)

print(f"Created {len(list(NB.glob('*.ipynb')))} notebooks")

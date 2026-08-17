"""Descriptive macroeconomic co-movement regressions."""

from __future__ import annotations

import pandas as pd
import statsmodels.api as sm

from portugal_fiscal_balance.schemas import SECTOR_BALANCE_PCT_GDP

BALANCE_COLUMNS = SECTOR_BALANCE_PCT_GDP


def build_macro_panel(balance_panel: pd.DataFrame, historical_macro: pd.DataFrame) -> pd.DataFrame:
    """Create a full nominal-GDP panel and attach historical labour controls where available."""
    frame = balance_panel[["year", "nominal_gdp_m_eur", *BALANCE_COLUMNS.values()]].copy()
    frame["nominal_gdp_growth"] = frame["nominal_gdp_m_eur"].pct_change(fill_method=None)
    frame["modern_regime"] = frame["year"].ge(1995).astype(int)
    labour = historical_macro.drop(columns=["nominal_gdp_m_eur", "source"], errors="ignore")
    frame = frame.merge(labour, on="year", how="left", validate="one_to_one")
    if "employment_k" in frame:
        frame["employment_growth"] = frame["employment_k"].pct_change(fill_method=None)
    return frame


def nominal_gdp_comovement_regressions(macro: pd.DataFrame) -> pd.DataFrame:
    """Estimate descriptive HAC regressions of balance ratios on nominal GDP growth.

    Nominal GDP growth is not labelled an output gap or a structural fiscal control.
    The coefficient is reported only as an empirical co-movement statistic.
    """
    records: list[dict[str, float | int | str]] = []
    for sector, outcome in BALANCE_COLUMNS.items():
        data = macro[[outcome, "nominal_gdp_growth", "modern_regime"]].dropna()
        x = sm.add_constant(data[["nominal_gdp_growth", "modern_regime"]])
        model = sm.OLS(data[outcome], x).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
        records.append(
            {
                "sector": sector,
                "n": int(model.nobs),
                "r_squared": float(model.rsquared),
                "nominal_gdp_growth_coef": float(model.params["nominal_gdp_growth"]),
                "nominal_gdp_growth_se_hac": float(model.bse["nominal_gdp_growth"]),
                "nominal_gdp_growth_pvalue_hac": float(model.pvalues["nominal_gdp_growth"]),
                "modern_regime_coef": float(model.params["modern_regime"]),
            }
        )
    return pd.DataFrame.from_records(records)


def historical_ssf_labour_regression(macro: pd.DataFrame) -> pd.DataFrame:
    """Estimate a small historical SSF co-movement model using employment and unemployment."""
    columns = ["social_security_balance_pct_gdp", "employment_growth", "unemployment_rate"]
    data = macro.loc[macro["year"].between(1978, 1995), columns].dropna()
    if len(data) < 10:
        return pd.DataFrame()
    x = sm.add_constant(data[["employment_growth", "unemployment_rate"]])
    model = sm.OLS(data["social_security_balance_pct_gdp"], x).fit(
        cov_type="HAC", cov_kwds={"maxlags": 1}
    )
    return pd.DataFrame(
        [
            {
                "n": int(model.nobs),
                "r_squared": float(model.rsquared),
                "employment_growth_coef": float(model.params["employment_growth"]),
                "employment_growth_se_hac": float(model.bse["employment_growth"]),
                "employment_growth_pvalue_hac": float(model.pvalues["employment_growth"]),
                "unemployment_rate_coef": float(model.params["unemployment_rate"]),
                "unemployment_rate_se_hac": float(model.bse["unemployment_rate"]),
                "unemployment_rate_pvalue_hac": float(model.pvalues["unemployment_rate"]),
            }
        ]
    )

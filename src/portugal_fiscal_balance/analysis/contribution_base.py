"""The contribution base: relating Social Security contributions to the wage bill.

Every earlier decomposition in this repository is internal to the fiscal accounts.
They establish that social contributions are the largest positive term in the recent
Social Security balance changes, and they stop there: an accounting location, not an
economic mechanism.

This module supplies the missing link. Contributions are levied predominantly on
wages, so the
natural base is the aggregate wage bill of the economy,

    W = N * wbar,

where ``N`` is employees and ``wbar`` average wages per employee. Writing the
contributions-to-wage-bill ratio as ``tau = C / W`` gives an exact decomposition of
the change in contributions into a wage-bill component, a ratio component and their
interaction, and a further split of the wage-bill component into employment and
average wages.

Two cautions apply throughout, and both concern what ``tau`` is not.

It is **not a statutory contribution rate**, which is why it is never called a rate
here. National-accounts social contributions
received by the Social Security Funds include imputed contributions and contributions
from bases other than employee wages, notably the self-employed. The ratio is an
ratio between two published aggregates, and it moves with coverage,
compliance and composition as well as with legislated rates.

It is **not causal.** A decomposition that assigns part of a movement to the wage bill
has not shown that the wage bill produced it; the accounting holds by construction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

#: The wage-bill measure used as the contribution base. Wages and salaries (D.11)
#: rather than compensation of employees (D.1), because D.1 already contains
#: employers' social contributions: using it would place part of the numerator
#: inside the denominator.
BASE_COLUMN: str = "wages_and_salaries_m_eur"


def contribution_base_panel(accounts: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """Join Social Security contributions to the national-accounts wage bill."""
    contributions = accounts.loc[
        accounts["sector"].eq("social_security_funds"),
        ["year", "social_contributions_m_eur", "nominal_gdp_m_eur"],
    ].rename(columns={"social_contributions_m_eur": "contributions_m_eur"})

    panel = base.merge(contributions, on="year", how="inner", validate="one_to_one")
    panel = panel.rename(columns={BASE_COLUMN: "wage_bill_m_eur"})
    panel["average_wage_eur"] = 1e3 * panel["wage_bill_m_eur"] / panel["employees_k"]
    panel["contributions_to_wage_bill_ratio"] = (
        panel["contributions_m_eur"] / panel["wage_bill_m_eur"]
    )
    panel["wage_bill_pct_gdp"] = 100.0 * panel["wage_bill_m_eur"] / panel["nominal_gdp_m_eur"]
    panel["contributions_pct_gdp"] = (
        100.0 * panel["contributions_m_eur"] / panel["nominal_gdp_m_eur"]
    )
    return panel.sort_values("year").reset_index(drop=True)


def _exact_product_decomposition(
    frame: pd.DataFrame, left: str, right: str, prefix: str
) -> pd.DataFrame:
    """Split the change in a product into its two factor effects and their interaction.

    For ``P = L * R`` the change decomposes without residual as

        dP = R_{t-1} dL + L_{t-1} dR + dL dR,

    which is an identity rather than an approximation. The interaction term is carried
    explicitly instead of being dropped or shared between the factors, since either of
    those would make the decomposition inexact while looking tidier.
    """
    out = pd.DataFrame({"year": frame["year"]})
    change_left = frame[left].diff()
    change_right = frame[right].diff()
    lagged_left = frame[left].shift()
    lagged_right = frame[right].shift()
    out[f"{prefix}_change"] = frame[left].mul(frame[right]).diff()
    out[f"{prefix}_from_left"] = lagged_right * change_left
    out[f"{prefix}_from_right"] = lagged_left * change_right
    out[f"{prefix}_interaction"] = change_left * change_right
    out[f"{prefix}_closure_error"] = out[f"{prefix}_change"] - (
        out[f"{prefix}_from_left"]
        + out[f"{prefix}_from_right"]
        + out[f"{prefix}_interaction"]
    )
    return out


def contribution_change_decomposition(panel: pd.DataFrame) -> pd.DataFrame:
    """Decompose the annual change in contributions into wage-bill and ratio components.

    Two nested exact decompositions. Contributions are the product of the effective
    ratio and the wage bill, so

        dC = tau_{t-1} dW + W_{t-1} dtau + dW dtau,

    and the wage bill is itself the product of employees and average wages, so the
    wage-bill component is itself the total of a second and separate application of
    the same identity, into an employment component, an average-wage component and
    their interaction. The two decompositions have different totals and neither is
    nested in the other.

    Both close by construction. The residual columns exist to demonstrate that, not to
    absorb anything.
    """
    frame = panel.sort_values("year").reset_index(drop=True)

    contributions = _exact_product_decomposition(
        frame, "contributions_to_wage_bill_ratio", "wage_bill_m_eur", "contributions"
    ).rename(
        columns={
            "contributions_change": "contributions_change_m_eur",
            "contributions_from_left": "from_ratio_m_eur",
            "contributions_from_right": "from_wage_bill_m_eur",
            "contributions_interaction": "wage_bill_ratio_interaction_m_eur",
            "contributions_closure_error": "contributions_closure_error_m_eur",
        }
    )

    # Employees are in thousands and the average wage in euro, so their product needs
    # scaling before it is comparable with a million-euro wage bill.
    scaled = frame.assign(average_wage_m_eur_per_k=frame["average_wage_eur"] / 1e3)
    wage_bill = _exact_product_decomposition(
        scaled, "employees_k", "average_wage_m_eur_per_k", "wage_bill"
    ).rename(
        columns={
            "wage_bill_change": "wage_bill_change_m_eur",
            "wage_bill_from_left": "from_employment_m_eur",
            "wage_bill_from_right": "from_average_wage_m_eur",
            "wage_bill_interaction": "employment_wage_interaction_m_eur",
            "wage_bill_closure_error": "wage_bill_closure_error_m_eur",
        }
    )

    merged = contributions.merge(wage_bill, on="year", how="inner", validate="one_to_one")
    merged = merged.merge(
        frame[["year", "contributions_m_eur", "wage_bill_m_eur", "contributions_to_wage_bill_ratio"]],
        on="year",
        how="left",
    )
    # The account panel has no 1996-1999 subsector components, so this panel jumps
    # from 1995 to 2000. Differencing across that jump would present a five-year
    # movement as an annual one, which is the error the rest of the analysis refuses
    # everywhere else.
    merged["year_gap"] = merged["year"].diff()
    merged = merged.loc[merged["year_gap"].eq(1.0)]
    return merged.dropna(subset=["contributions_change_m_eur"]).reset_index(drop=True)


def symmetric_contribution_decomposition(panel: pd.DataFrame) -> pd.DataFrame:
    """Re-run the decomposition with the interaction split evenly between the factors.

    The baseline decomposition evaluates each factor effect at the previous year and
    carries the interaction as its own term. That is exact but it is a convention: the
    interaction could equally be attributed to either factor, or shared. The symmetric
    alternative evaluates each effect at the midpoint,

        dC = ((tau_t + tau_{t-1}) / 2) dW + ((W_t + W_{t-1}) / 2) dtau,

    which is also exact and distributes the interaction evenly by construction, leaving
    no residual term at all.

    Neither is more correct. Reporting both is what shows that a conclusion about which
    component dominates is a property of the data rather than of the allocation rule.
    """
    frame = panel.sort_values("year").reset_index(drop=True)
    ratio = frame["contributions_to_wage_bill_ratio"]
    wage_bill = frame["wage_bill_m_eur"]

    out = pd.DataFrame({"year": frame["year"]})
    out["contributions_change_m_eur"] = frame["contributions_m_eur"].diff()
    out["from_wage_bill_m_eur"] = 0.5 * (ratio + ratio.shift()) * wage_bill.diff()
    out["from_ratio_m_eur"] = 0.5 * (wage_bill + wage_bill.shift()) * ratio.diff()
    out["closure_error_m_eur"] = out["contributions_change_m_eur"] - (
        out["from_wage_bill_m_eur"] + out["from_ratio_m_eur"]
    )
    out["wage_bill_share_of_change"] = np.where(
        out["contributions_change_m_eur"].abs().gt(1e-9),
        out["from_wage_bill_m_eur"] / out["contributions_change_m_eur"],
        np.nan,
    )
    # The same gap rule as the baseline: no change spans 1995 to 2000.
    out = out.loc[frame["year"].diff().eq(1.0)]
    return out.dropna(subset=["contributions_change_m_eur"]).reset_index(drop=True)


def contribution_wage_bill_regression(panel: pd.DataFrame) -> pd.DataFrame:
    """Regress the change in contributions on the change in the wage bill.

    This is the specification the review named, reported as a companion to the
    decomposition rather than as a substitute for it. Its merit over the earlier
    nominal-GDP regression is that the regressor is a quantity the levy is charged
    on. A slope near the average contributions-to-wage-bill ratio is what a broadly
    stable ratio would produce; it does not follow from the identity, because the ratio
    and interaction terms could co-move with the wage-bill change.

    Both variables are first differences of levels in the same unit, so the slope
    reads directly as euro of contributions per euro of wage bill. No causal claim
    attaches to it.
    """
    data = panel[["year", "contributions_m_eur", "wage_bill_m_eur"]].copy()
    data["contributions_change"] = data["contributions_m_eur"].diff()
    data["wage_bill_change"] = data["wage_bill_m_eur"].diff()
    # No change is estimated across the 1995-to-2000 source gap.
    data = data.loc[data["year"].diff().eq(1.0)]
    data = data.dropna(subset=["contributions_change", "wage_bill_change"])
    if len(data) < 10:
        return pd.DataFrame()

    design = sm.add_constant(data[["wage_bill_change"]])
    model = sm.OLS(data["contributions_change"], design).fit(
        cov_type="HAC", cov_kwds={"maxlags": 2}
    )
    mean_rate = float(panel["contributions_to_wage_bill_ratio"].mean())
    slope = float(model.params["wage_bill_change"])
    return pd.DataFrame.from_records(
        [
            {
                "n": int(model.nobs),
                "first_year": int(data["year"].min()),
                "last_year": int(data["year"].max()),
                "r_squared": float(model.rsquared),
                "wage_bill_coef": slope,
                "wage_bill_se_hac": float(model.bse["wage_bill_change"]),
                "wage_bill_pvalue_hac": float(model.pvalues["wage_bill_change"]),
                "intercept_m_eur": float(model.params["const"]),
                "mean_ratio": mean_rate,
                "coef_minus_mean_ratio": slope - mean_rate,
            }
        ]
    )

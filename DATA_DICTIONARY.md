# Data dictionary

## `data/processed/fiscal_balances_1977_2025.csv`

| Column | Definition |
|---|---|
| `year` | Calendar year |
| `general_government_balance_m_eur` | General Government B.9, million euro |
| `central_government_balance_m_eur` | Central Government B.9, million euro |
| `regional_local_balance_m_eur` | Regional and Local Government B.9, million euro |
| `social_security_balance_m_eur` | Social Security Funds B.9, million euro |
| `*_pct_gdp` | Corresponding balance divided by nominal GDP |
| `closure_error_m_eur` | GG B.9 minus the sum of the three subsectors |
| `closure_within_tolerance` | Whether absolute closure error is at most 2 M€ |
| `statistical_regime` | Historical or modern source regime |
| `vintage_status` | `final` or `provisional`, as flagged by the publisher. Historical years are `final`; the most recent modern years are `provisional` and will be revised |
| `known_methodology_break` | True for 1995 |

## `data/processed/annual_balance_metrics_1977_2025.csv`

Adds:

| Column | Definition |
|---|---|
| `non_ssf_balance_m_eur` | Central + Regional/Local balance |
| `aggregate_balance_positive` | General Government balance > 0 |
| `ssf_balance_positive` | SSF balance > 0 |
| `non_ssf_balance_negative` | Central + Regional/Local balance < 0 |
| `positive_aggregate_with_negative_non_ssf_balance` | Descriptive conjunction of those signs |
| `ssf_exceeds_aggregate_balance` | SSF balance exceeds positive aggregate B.9 |
| `ssf_offset_ratio` | SSF balance divided by absolute negative non-SSF balance |
| `ssf_required_to_offset_non_ssf_m_eur` | Magnitude of negative non-SSF balance, else zero |
| `ssf_balance_after_offset_m_eur` | SSF balance minus required offset amount |

## `data/processed/subsector_accounts_1977_2025.csv`

Long sector-year table. Depending on source availability it includes:

- total/current/capital revenue;
- tax revenue;
- social contributions;
- total/primary/current expenditure;
- compensation of employees;
- intermediate consumption;
- social transfers;
- subsidies;
- interest;
- GFCF;
- B.9 balance;
- primary balance;
- nominal GDP;
- source and statistical regime.

The table intentionally has no 1996–1999 observations for detailed Central, Regional/Local and SSF components.

## `outputs/tables/balance_change_attribution.csv`

One row per adjacent-year pair of the canonical panel.

| Column | Definition |
|---|---|
| `aggregate_change_m_eur` | Annual change in the General Government balance |
| `central_change_m_eur`, `regional_local_change_m_eur`, `ssf_change_m_eur` | The subsector changes that compose it |
| `change_closure_error_m_eur` | Aggregate change minus the sum of the three, inheriting the sources' 1 M€ rounding |
| `*_share_abs_aggregate_change` | Each subsector change divided by the absolute aggregate change |
| `*_change_pct_gdp` | The same changes divided by current-year nominal GDP |

The `_pct_gdp` columns share one denominator, so they decompose additively:
\(\Delta B/GDP = \Delta B^{C}/GDP + \Delta B^{RL}/GDP + \Delta B^{SSF}/GDP\).
This is **not** the change in the balance ratio, which would also move with the
denominator. The scaling exists only so that years are comparable in size: ranking
movements on nominal euro effectively ranks them by how recent they are.

## `outputs/tables/largest_balance_movements.csv`

The largest annual movements **within each statistical regime**, ranked on the absolute value
of `aggregate_change_pct_gdp`. Ranking is per regime, not across both: each change is computed
inside one source family, but ordering historical against modern episodes by size would compare
two methodologies. 1995 is excluded because that change straddles the splice in both panels.

| Column | Definition |
|---|---|
| `regime`, `rank_in_regime` | Statistical regime and rank inside it |
| `direction` | `improvement` or `deterioration`, derived from the sign |
| `dominant_subsector` | Subsector with the largest absolute contribution, as a readable label |
| `dominant_subsector_change_m_eur` | That subsector's own balance change |
| `dominant_subsector_share` | Its contribution divided by the absolute aggregate change |
| `dominant_revenue_change_m_eur`, `dominant_expenditure_change_m_eur` | **That subsector's** revenue and expenditure changes, from the detailed account panel |
| `dominant_expenditure_contribution_m_eur` | Minus the expenditure change: the sign with which expenditure enters the balance |
| `dominant_split_error_m_eur` | Subsector balance change minus (revenue − expenditure) change; the two source families are not forced to agree |
| `account_balance_change_m_eur`, `source_family_difference_m_eur` | The aggregate change as measured by the account panel, and its gap from the canonical measure |

The attribution is hierarchical: the revenue and expenditure columns describe the *named
subsector*, not the aggregate, so both halves of the table refer to one entity.

## `outputs/tables/account_component_changes.csv`

Long panel: one row per sector-year-component. Each annual revenue and expenditure change
decomposed into the components that produced it.

| Column | Definition |
|---|---|
| `component_scheme` | `modern_detailed` (four revenue and seven expenditure components) or `historical_current_capital` (current against capital only) |
| `side`, `component` | Revenue or expenditure, and the readable component name |
| `change_m_eur` | The movement in the component itself |
| `contribution_m_eur` | That movement's effect on the balance: revenue positive, expenditure negated |
| `balance_change_m_eur`, `component_closure_error_m_eur` | The change being decomposed, and the residual of the contributions summing to it |

The two source families resolve the accounts at different depths and are **not** forced onto
a common scheme. Each sector-year uses the finer scheme it reports: coarsening the modern
period would discard real detail, and assigning modern component names to historical
movements would fabricate it. No change is computed across a source gap.

## `outputs/tables/episode_component_attribution.csv`

The three largest component movements behind each ranked episode of
`largest_balance_movements.csv`, joined on the subsector that dominates the episode so that
aggregate, subsector and account levels all describe one entity. Components are ranked by the
absolute size of their contribution, so a large expenditure rise and a large revenue rise
compete on the same footing.

## `outputs/tables/ssf_balance_change_decomposition.csv`

Each annual change in the Social Security balance split into the account movements that
produced it. No change is computed across the 1995-to-2000 source gap.

| Column | Definition |
|---|---|
| `balance_change_m_eur`, `revenue_change_m_eur`, `expenditure_change_m_eur` | The identity ΔB = ΔR − ΔE |
| `contributions_change_m_eur`, `other_revenue_change_m_eur` | Revenue split; available for the whole detailed panel |
| `social_transfers_change_m_eur`, `other_expenditure_change_m_eur` | Expenditure split; modern period only, where component detail exists |
| `*_contribution_m_eur` | The same terms carrying the sign with which they enter the balance: revenue positive, expenditure negated |
| `revenue_split_error_m_eur`, `expenditure_split_error_m_eur` | Residuals of the two splits |
| `balance_identity_error_m_eur`, `contribution_closure_error_m_eur` | Residuals of ΔB = ΔR − ΔE and of the four contributions summing to ΔB |

**Signs are the point of this table.** Expenditure enters the balance negatively, so a rise in
social transfers *reduces* the balance. The `*_contribution_*` columns sum to the balance
change; the plain `*_change_*` columns do not, and placing a raw expenditure change beside a
balance change invites adding two quantities of opposite sign.

## `outputs/tables/persistence_by_regime.csv`

`persistence_summary.csv` split by statistical regime. Sign counts, mean, median, minimum
and maximum per sector and regime. Runs are deliberately **not** recomputed per regime: a
run is a property of the uninterrupted series, and truncating it at a window boundary would
report the length of the window.

## `outputs/tables/structural_break_bic_ladder.csv`

BIC of every admissible break count under the preferred specification, with
`delta_bic_vs_best` and a `selected` flag. Publishing only the chosen count hides how close
the alternatives were.

## `outputs/tables/structural_break_sensitivity.csv`

Detection re-run over the full tuning grid: `min_segment` in {4, 5, 6, 7} crossed with
`max_breaks` in {1, 2, 3}, giving twelve specifications per regime-sector series.

## `outputs/tables/structural_break_stability.csv`

Summary of that grid.

| Column | Definition |
|---|---|
| `modal_n_breaks`, `modal_n_breaks_share` | Most frequent break count and the fraction of specifications selecting it |
| `modal_break_years`, `modal_break_years_share` | Most frequent set of dates and the fraction of specifications returning exactly it |
| `n_distinct_break_year_sets` | How many different date sets the grid produced |

`modal_break_years_share` is the quantity that decides whether a date can be stated as
detected or only as a candidate. A break year should not be quoted without it.

## `outputs/tables/primary_balance_sign_summary.csv`

Headline against primary balance sign frequencies per sector, over the sector-years for
which interest expenditure exists. `primary_positive_year_list` is a semicolon-separated
list of the years with a positive primary balance. Central Government records a negative
B.9 in every observed year while its primary balance is positive in a substantial minority
of them, so the two counts must be read together.

## `outputs/tables/primary_balance_sign_summary_by_regime.csv`

The same summary computed inside each statistical regime. The counts partition the
pooled table exactly. The split exists because `mean_interest_pct_gdp` and
`max_interest_pct_gdp` are magnitudes: Central Government interest averages 5.52% of
GDP historically against 3.19% in the modern regime, so the pooled 4.17% describes
neither period. Sign counts survive pooling and are reported both ways.

## `outputs/tables/ssf_accounting_boundary_comparison.csv`

The ESA 2010 Social Security Funds balance beside the CFP budget-system total, with
`boundary_difference_m_eur`. The two are **different accounting objects** and are never
added, netted or reconciled. The difference is non-zero in every overlapping year, which is
why a figure quoted from the budget documents cannot be substituted for the
national-accounts one.

## `outputs/tables/source_validation_summary.csv`

Every cross-check in one unit, so two different kinds of test can be compared directly.

| `check` value | Question it answers |
|---|---|
| `Accounting identity` | Is the extraction arithmetically self-consistent? |
| `Source agreement` | Do two independently published sources report the same number? |
| `Vintage revision` | How much did the 1995 restatement move? |

Identity closure does not imply source agreement: the identities close to rounding while
the largest source disagreement is a Central Government difference of about 67 M€.

## `data/processed/european_subsector_panel_1995_2025.csv`

Country-year panel built from the bundled Eurostat snapshot, used only for the benchmark.

| Column | Definition |
|---|---|
| `general_government_mio_nac`, `social_security_mio_nac` | B.9 in millions of national currency |
| `non_ssf_mio_nac` | Central **plus state plus local** government. Including the state tier is what makes federal and unitary reporters comparable; a missing tier contributes zero because it does not exist |
| `state_government_mio_nac`, `has_state_tier` | The state tier itself, kept visible so its size is checkable |
| `*_pct_gdp` | The same quantities as published shares of GDP, to one decimal |
| `closure_error_mio_nac` | Aggregate minus the sum of the two component groups |
| `sectors_reported`, `complete` | How many of the four required sectors the country-year reports |
| `offset_ratio` | Social Security balance over the absolute non-Social-Security balance, in national currency, defined only where the latter is negative, the former positive, and the denominator at least 0.5% of GDP |

Ratios use national currency because the published shares of GDP carry one decimal, which is
too coarse a denominator: a balance printed as −0.2 could lie anywhere in a band wide enough
to move the ratio by a quarter of its value.

## `outputs/tables/european_benchmark_summary.csv`

One row per reporter with at least fifteen complete years. Sign frequencies, mean Social
Security balance, count of aggregate-surplus years and — the structural comparison —
`n_aggregate_positive_with_negative_non_ssf`, the number of those surplus years in which the
non-Social-Security balance was negative.

## `outputs/tables/european_benchmark_position.csv`

One row per metric giving Portugal's value, the cross-country median, minimum, maximum and
percentile rank, so a claim that Portugal is or is not unusual can be read off rather than
asserted.

## `data/processed/contribution_base_panel_1995_2025.csv`

Social Security contributions joined to the national-accounts wage bill.

| Column | Definition |
|---|---|
| `wage_bill_m_eur` | Wages and salaries (D.11), total economy |
| `compensation_of_employees_m_eur` | Compensation of employees (D.1), retained for comparison but **not** used as the base: it contains employers' social contributions |
| `employees_k`, `employment_k` | Employees and total employment, domestic concept, thousands |
| `average_wage_eur` | Wage bill divided by employees |
| `contributions_to_wage_bill_ratio` | Contributions divided by the wage bill. A ratio between two published aggregates, **not** a statutory rate: its numerator contains revenue raised on bases its denominator does not measure, so it moves with coverage, compliance and composition as well as with legislated rates |

## `outputs/tables/contribution_change_decomposition.csv`

Two exact identities, applied to two different quantities. They are **not** nested:

- the change in contributions,
  `\Delta C = \tau_{t-1}\,\Delta W + W_{t-1}\,\Delta\tau + \Delta W\,\Delta\tau`;
- the change in the wage bill itself,
  `\Delta W = \bar{w}_{t-1}\,\Delta N + N_{t-1}\,\Delta\bar{w} + \Delta N\,\Delta\bar{w}`.

`from_wage_bill_m_eur`, `from_ratio_m_eur` and `wage_bill_ratio_interaction_m_eur` sum to
`contributions_change_m_eur`. `from_employment_m_eur`, `from_average_wage_m_eur` and
`employment_wage_interaction_m_eur` sum to `wage_bill_change_m_eur` — a different and much
larger total. The second trio decomposes `\Delta W`, not the wage-bill component of
`\Delta C`; what links them is the factor `\tau_{t-1}`. Reading the employment and
average-wage columns as parts of `from_wage_bill_m_eur` is a mathematical error and the
two are reported as separate tables for that reason.

The interaction columns are carried rather than dropped or shared between the factors, and
the closure columns exist to demonstrate exactness. No change is computed across the
1995-to-2000 source gap: bridging it would treat a five-year movement as annual.

## `outputs/tables/contribution_symmetric_decomposition.csv`

The same change under the symmetric (midpoint) convention,
`\Delta C = \tfrac{1}{2}(\tau_t+\tau_{t-1})\,\Delta W
+ \tfrac{1}{2}(W_t+W_{t-1})\,\Delta\tau`, which is exact in two terms because it splits
the interaction evenly between the factors. `wage_bill_share_of_change` is the wage-bill
term as a share of the total. Neither convention is more correct; this table exists so the
reading does not rest on the choice, and each factor here differs from its counterpart in
the exact table by exactly half the interaction.

## `outputs/tables/contribution_wage_bill_regression.csv`

The change in contributions regressed on the change in the wage bill, HAC standard errors.
`coef_minus_mean_ratio` is the slope less the mean contributions-to-wage-bill ratio. The
identity delivers a slope equal to the mean ratio only if `\Delta\tau` and the
interaction are uncorrelated with `\Delta W`, which nothing here establishes, so their
closeness is a descriptive fact about this sample rather than an arithmetic necessity.

## Main output metrics

### SSF offset ratio

\[
O_t=\frac{B^{SSF}_t}{|B^{C}_t+B^{RL}_t|}
\]

only when the non-SSF balance is negative and the SSF balance is positive.

### Primary balance

\[
PB=B.9+Interest.
\]

### Balance before GFCF diagnostic

\[
B^{before\ GFCF}=B.9+GFCF.
\]

### Debt reconciliation error

\[
Error=\Delta Debt+B.9-SFA.
\]

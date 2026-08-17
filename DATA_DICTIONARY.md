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

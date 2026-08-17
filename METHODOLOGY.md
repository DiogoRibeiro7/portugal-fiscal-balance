# Methodology

## 1. Unit of analysis

The principal unit is the calendar year from 1977 to 2025 inclusive.

The primary fiscal measure is B.9, net lending (+) / net borrowing (-).

## 2. Subsector decomposition

The canonical decomposition is

\[
B^{GG}_t = B^{C}_t + B^{RL}_t + B^{SSF}_t.
\]

The repository tests this identity for every year and preserves the residual as `closure_error_m_eur`.

## 3. Source splice

The canonical B.9 panel uses:

- 1977–1994: Banco de Portugal / INE historical long series;
- 1995–2025: INE via PORDATA;
- 1995 historical observation: retained only as an explicit overlap diagnostic;
- CFP modern workbooks: independent validation and detailed account components.

No smoothing or calibration is applied across 1995.

## 4. Detailed account panel

For General Government, detailed account components use:

- 1977–1994 historical long series;
- 1995–2025 CFP ESA 2010 workbook.

For Central Government, Regional/Local Government and Social Security Funds:

- 1977–1995 historical long series;
- 2000–2025 CFP ESA 2010 workbook.

The 1996–1999 subsector component gap is not imputed.

## 5. Balance offset metrics

Define

\[
B^{nonSSF}_t = B^{C}_t + B^{RL}_t.
\]

When `B_nonSSF < 0` and `B_SSF > 0`, the SSF offset ratio is

\[
O_t = \frac{B^{SSF}_t}{|B^{nonSSF}_t|}.
\]

`O_t = 1` means the positive SSF balance equals the magnitude of the negative non-SSF balance. The metric is an accounting ratio, not a causal counterfactual.

## 6. Year-to-year attribution

The aggregate annual change is decomposed exactly:

\[
\Delta B^{GG}_t
= \Delta B^{C}_t
+ \Delta B^{RL}_t
+ \Delta B^{SSF}_t.
\]

## 7. Revenue/expenditure decomposition

For each sector and year with detailed accounts:

\[
B_{i,t}=R_{i,t}-E_{i,t}
\]

and for adjacent years within a continuous source block:

\[
\Delta B_{i,t}=\Delta R_{i,t}-\Delta E_{i,t}.
\]

No annual change is computed across the 1995-to-2000 gap in modern subsector account components.

## 8. Persistence

Each annual balance is classified by sign. The repository reports:

- positive and negative observation counts;
- mean and median balance as percentage of GDP;
- longest positive and negative runs;
- empirical one-year sign transition probabilities.

## 9. Structural mean shifts

A short annual sample does not justify a highly flexible change-point model. The repository therefore uses a piecewise-constant mean model with:

- at most two breaks per statistical regime;
- minimum segment length of five years;
- dynamic-programming minimisation of within-segment SSE;
- BIC model selection.

Detection is performed separately for 1977–1994 and 1995–2025 so the known statistical splice is not treated as a candidate economic break.

## 10. Social Security analyses

Two layers are kept separate:

1. ESA 2010 Social Security Funds national accounts;
2. CFP Social Security budget-system tables.

The first is used for the B.9 decomposition. The second is used for the internal Previdential / Citizenship / Special Regimes analysis.

The repository does not subtract all State transfers from the SSF balance and label the result an underlying balance.

## 11. Intergovernmental-transfer sensitivity

Historical source tables allow a mechanical sensitivity:

\[
B^{sens}_{i,t}
=
B_{i,t}-(T^{received}_{i,t}-T^{paid}_{i,t}).
\]

This only changes the recorded location of transfers mechanically. It is not treated as a counterfactual in which the associated expenditure responsibilities disappear.

## 12. Primary balance

Primary balance is reconstructed as

\[
PB_{i,t}=B_{i,t}+Interest_{i,t}.
\]

The repository checks this against the published modern primary-balance row where available.

## 13. Fixed-capital-formation diagnostic

The analytical diagnostic

\[
B^{before\ GFCF}_{i,t}=B_{i,t}+GFCF_{i,t}
\]

is reported only to quantify the scale of fixed-capital formation relative to B.9. It is not an official fiscal-balance definition.

## 14. Debt-flow reconciliation

For modern CFP data:

\[
\Delta Debt_t = -B_t + SFA_t.
\]

The pipeline calculates and validates the reconciliation residual.

## 15. Macroeconomic co-movement

The full-period regression uses nominal GDP growth because it is consistently reconstructible from the bundled sources across 1977–2025.

For each subsector:

\[
B_{i,t}/GDP_t
=
\alpha_i
+
\beta_i g^{nominal}_t
+
\gamma_i I(t\ge 1995)
+
\epsilon_{i,t}.
\]

HAC standard errors are used. This is explicitly a descriptive co-movement model, not an output-gap model and not a causal estimate.

For 1978–1995, the historical workbook also permits a small SSF model using employment growth and unemployment rate.

## 16. Reproducibility rules

- raw source files are retained;
- source-specific extracted files are persisted in `data/interim/`;
- processed panels are persisted separately;
- all calculated analysis tables are saved to CSV;
- notebooks are generated from `scripts/create_notebooks.py` and committed with their
  executed outputs, so the narrative is readable without running anything;
- notebook figures are produced by the same functions that write `outputs/figures/`;
- raw source SHA-256 hashes are recorded;
- the report is generated from persisted outputs.

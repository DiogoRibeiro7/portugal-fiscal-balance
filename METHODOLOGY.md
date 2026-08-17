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

No smoothing or calibration is applied across 1995. Two consequences are enforced
throughout: no statistic whose value depends on the *level* of the balance is averaged
across the splice, and no annual change is computed through it.

The publisher's `final` / `provisional` flag is carried into the canonical panel as
`vintage_status`. The most recent years are provisional and will be restated by a later
vintage; they are also the years the report discusses in most detail.

### 3.1 Identity closure and source agreement are different tests

Both are reported, in one unit, in `outputs/tables/source_validation_summary.csv`.

An **identity** check asks whether the extraction is arithmetically self-consistent. It can
close to numerical precision while both sources are wrong in the same way, because it never
consults a second source.

A **source-agreement** check asks whether two independently published sources report the
same number for the same year. Identity closure cannot establish it.

The distinction is not hypothetical here: the identities close to the sources' 1 M€
rounding, while the largest disagreement between the PORDATA bridge and the CFP workbook is
a Central Government difference of roughly 67 M€.

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

Changes are also reported scaled by current-year nominal GDP. Because the terms then share
one denominator, the scaled version decomposes exactly as well:

\[
\frac{\Delta B^{GG}_t}{GDP_t}
= \frac{\Delta B^{C}_t}{GDP_t}
+ \frac{\Delta B^{RL}_t}{GDP_t}
+ \frac{\Delta B^{SSF}_t}{GDP_t}.
\]

This is deliberately **not** the change in the balance ratio, which would also move with the
denominator and would therefore not decompose additively. The scaling exists so that years
are comparable in size: ranking movements on nominal euro effectively ranks them by how
recent they are, since 2025 nominal GDP is orders of magnitude above 1977.

`outputs/tables/largest_balance_movements.csv` ranks the five largest improvements and the
five largest deteriorations on that scaled measure, names the subsector accounting for most
of each move, and attaches the revenue and expenditure changes from the detailed account
panel. The two panels are different source families, so the residual between their measures
of the same annual change is carried as its own column rather than reconciled away. 1995 is
excluded because the 1994-to-1995 change straddles the vintage splice in both panels.

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

### 8.1 Pooled and per-regime summaries

`persistence_summary.csv` pools the whole panel; `persistence_by_regime.csv` splits it at
the 1995 splice. The split is the form in which magnitudes should be read, because the two
regimes differ enough that the pooled mean describes neither: the aggregate balance averages
−6.43% of GDP over 1977–1994 and −4.04% over 1995–2025, against a pooled −4.92% that
corresponds to no observed period.

Sign counts are far more robust to pooling, since a sign does not depend on the level
convention of the vintage. Runs are **not** recomputed per regime: a run is a property of the
uninterrupted series, and truncating it at a window boundary would report the length of the
window rather than the length of the run.

## 9. Structural mean shifts

A short annual sample does not justify a highly flexible change-point model. The repository therefore uses a piecewise-constant mean model with:

- at most two breaks per statistical regime;
- minimum segment length of five years;
- dynamic-programming minimisation of within-segment SSE;
- BIC model selection.

Detection is performed separately for 1977–1994 and 1995–2025 so the known statistical splice is not treated as a candidate economic break.

Segment means and break locations are both counted as free parameters in the BIC. That is
the conservative choice: it penalises an extra break twice and makes the model less willing
to claim one.

### 9.1 Why break dates are reported as candidates

With eighteen or thirty-one annual observations per regime, a single selected date is not
determined by the data. Three guards are persisted rather than asserted.

1. **BIC margin** (`structural_breaks.csv`): how much better the selected break count scores
   than the next-best count.
2. **BIC ladder** (`structural_break_bic_ladder.csv`): the score of every admissible count,
   including zero breaks, so the alternatives are visible.
3. **Sensitivity grid** (`structural_break_sensitivity.csv`, summarised in
   `structural_break_stability.csv`): detection re-run over `min_segment` in {4, 5, 6, 7}
   crossed with `max_breaks` in {1, 2, 3}, twelve specifications per series.

Neither tuning parameter is estimated from the data, so a date surviving only one of their
values is a property of that choice rather than of the series. `modal_break_years_share` is
the fraction of the grid returning exactly the modal set of dates, and it is what decides
whether a date may be stated as detected or only as a candidate. A break year should not be
quoted from this repository without it.

## 10. Social Security analyses

Two layers are kept separate:

1. ESA 2010 Social Security Funds national accounts;
2. CFP Social Security budget-system tables.

The first is used for the B.9 decomposition. The second is used for the internal Previdential / Citizenship / Special Regimes analysis.

The repository does not subtract all State transfers from the SSF balance and label the result an underlying balance.

### 10.1 Quantifying the boundary, not closing it

`ssf_accounting_boundary_comparison.csv` places the two side by side and reports their
difference. They are never added, netted or reconciled: they are different accounting
objects, and the table measures how far apart they are rather than bridging them.

The difference is small relative to the balances but non-zero in every overlapping year.
That is the point. A Social Security figure quoted from the budget documents is not the
figure that enters the national-accounts identity, and the two cannot be substituted for one
another.

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

### 12.1 Headline and primary signs are different facts

`primary_balance_sign_summary.csv` reports both sign frequencies per sector, because reading
one without the other supports a conclusion the data do not.

Central Government records a negative B.9 in every year of the canonical panel. Over the 45
years for which interest expenditure exists, its primary balance is nevertheless positive in
15 of them, and those years are not confined to the recent period. Both statements are
descriptive and they are not in conflict: interest is the arithmetic that separates them.

A positive primary balance is not a sustainability result and a negative headline balance is
not an unsustainability result. The primary balance excludes interest by construction and
says nothing about the debt path on its own.

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

### 15.1 Why this is appendix material

These estimates are confined to an appendix of the report, and nothing in its body depends on
them. The specification is weak in ways caveat wording does not repair:

1. the dependent variable carries nominal GDP in its denominator while the regressor is the
   growth rate of that same quantity, so part of any measured association is mechanical;
2. with \(g^{nominal}\approx g^{real}+\pi\), one coefficient is asked to represent both real
   growth and inflation;
3. the \(R^2\) values are very low and no nominal-growth coefficient reaches conventional
   significance under HAC standard errors;
4. the labour specification rests on eighteen observations, at which size the positive
   unemployment coefficient should not be interpreted at all — trends, collinearity between
   the labour series, dynamic specification and the time-series properties of the variables
   are all unexamined.

A specification with a clearer mechanism would model the Social Security contribution base
directly, regressing the change in contributions on the change in the aggregate wage bill
\(W_t=N_t\bar w_t\) rather than on aggregate nominal growth. That is not implemented.

## 16. Reproducibility rules

- raw source files are retained;
- source-specific extracted files are persisted in `data/interim/`;
- processed panels are persisted separately;
- all calculated analysis tables are saved to CSV;
- notebooks are generated from `scripts/create_notebooks.py` and committed with their
  executed outputs, so the narrative is readable without running anything;
- notebook figures are produced by the same functions that write `outputs/figures/`;
- raw source SHA-256 hashes are recorded;
- the report is generated from persisted outputs, and its appendix maps every section to
  the notebook that produces it and the artefact it reads.

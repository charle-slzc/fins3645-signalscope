# AI Log 05 - Phase 2C Matched-Shrinkage Falsification

## Prompt Recorded

The student requested a documentation and empirical readout pass for Phase 2C,
after a previous Codex session implemented the matched-shrinkage placebo test but
lost its remote connection during final verification. The student explicitly
instructed that Phase 2C must not be rewritten or reimplemented, and that no
Phase 1, Phase 2A, Phase 2B, Phase 2C analytical code or existing analytical
result should be modified.

This log records the Phase 2C falsification design, the artifact readout, and the
limits of what is auditable from disk.

## Skeptical Objection

Phase 2B showed that the SignalScope Confidence Lens attenuates sentiment tilts
and reduces turnover relative to the Standard Sentiment overlay. The skeptical
objection is that this may not prove a useful dynamic evidence-aware mechanism.
The Confidence Lens might simply behave like a smaller constant sentiment
coefficient. If so, the observed reduction in portfolio disturbance would be a
generic shrinkage effect rather than evidence that breadth and agreement
dynamically identify which sentiment signals deserve stronger or weaker
treatment.

## Why The Matched-Shrinkage Placebo Was Introduced

The matched-shrinkage placebo was introduced to separate two explanations:

- constant shrinkage: the overlay improves only because all sentiment tilts are
  scaled down by roughly the same amount;
- dynamic selectivity: the overlay changes which sector-date signals are
  attenuated or preserved based on evidence breadth and sentiment agreement.

The placebo keeps the same sentiment direction and the same aggregate
pre-renormalisation absolute tilt magnitude as the Confidence Lens, but replaces
dynamic confidence with one global constant. This creates a direct falsification
benchmark for the Confidence Lens.

## Exact Definitions

`C_mean` is the simple average of the Phase 2B confidence values across valid
rebalance-sector observations:

`C_mean = mean(C_i)`

where `C_i` is the Confidence Lens evidence-confidence value for observation
`i`.

`C_match` is the absolute-signal-weighted confidence constant:

`C_match = sum(|Z*_i| * C_i) / sum(|Z*_i|)`

where `Z*_i` is the clipped cross-sectional sector sentiment direction used by
Phase 2B.

The Matched-Shrinkage Placebo uses the same sentiment direction as Standard
Sentiment, but applies one global constant:

`placebo_tilt_i = tilt_strength * Z*_i * C_match`

The Confidence Lens tilt is:

`confidence_tilt_i = tilt_strength * Z*_i * C_i`

`SelectiveDeviation` is the absolute difference between the dynamic Confidence
Lens tilt and the matched constant placebo tilt:

`SelectiveDeviation_i = |confidence_tilt_i - placebo_tilt_i|`

## Why C_match Is Stronger Than Mean Confidence

`C_mean` treats every rebalance-sector observation equally. That is not the right
constant for testing whether the Confidence Lens merely shrinks sentiment signal
strength, because observations with larger `|Z*|` contribute more to aggregate
tilt.

`C_match` weights confidence by `|Z*|`, so the placebo matches the Confidence
Lens on aggregate pre-renormalisation absolute tilt magnitude. This makes the
test stricter than using `C_mean`: the placebo is not merely an average
confidence rule, but a constant-shrinkage rule calibrated to the same total
signal-strength budget.

## Additive Implementation

Phase 2C was implemented additively in:

- `src/placebo.py`
- `scripts/run_phase2c.py`
- `tests/test_placebo_falsification.py`

The new runner consumes frozen Phase 1, Phase 2A, and Phase 2B artifacts and
writes only Phase 2C outputs. It does not replace the existing Phase 1, Phase 2A,
or Phase 2B build path.

## Development Issue And Correction

During development, some presentation cases had essentially zero base sector
weight. Those cases could be mathematically valid but weak for explanation,
because changes in a nearly unheld sector have little portfolio relevance.

The correction changed deterministic case selection to prefer non-trivial base
sector exposure where available. The selection rule remains based on signal and
evidence state only, and the output case table records that no subsequent
returns were used:

`deterministic from signal/evidence state only; no subsequent returns used`

## Verification Status

The previous remote Codex session reported that Phase 2C synthetic tests passed,
that the Phase 2C runner generated additive artifacts, and that frozen Phase
1/2A/2B artifact hashes were unchanged. However, the remote Codex transport
failed before that session could complete final verification.

The original pre-crash before/after hashes were not persisted, so the first
execution is not independently auditable from the current disk state alone. The
current Phase 2C runner contains a before/after frozen-artifact hash guard. A
latest local rerun can support only this narrower statement: if that rerun
passed the guard, then the latest verified execution left those frozen artifacts
unchanged.

Final local verification transcript provided by the student:

```text
32 passed in 74.65s (0:01:14)

21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

## Generated Phase 2C Artifacts Read

- `results/data/fusion_placebo_returns.csv`
- `results/data/fusion_placebo_weights.csv`
- `results/tables/confidence_placebo_comparison.csv`
- `results/tables/confidence_placebo_selectivity.csv`
- `results/tables/confidence_placebo_quadrants.csv`
- `results/tables/confidence_placebo_sector_year.csv`
- `results/tables/confidence_placebo_cases.csv`
- `results/tables/confidence_placebo_turnover_decomposition.csv`
- `results/figures/confidence_vs_constant_shrinkage.png`

## Empirical Readout

The Phase 2C selectivity table contains 360 valid rebalance-sector observations.

- `C_mean`: `0.6591585049725245`
- `C_match`: `0.6322361773345248`
- Standard absolute tilt sum: `27.66598810891609`
- Confidence absolute tilt sum: `17.491438564163516`
- Placebo absolute tilt sum: `17.491438564163516`
- Placebo minus Confidence aggregate absolute tilt difference: `0.0`

This proves that the matched placebo has the same aggregate
pre-renormalisation absolute tilt magnitude as the Confidence Lens in the saved
Phase 2C artifacts.

For the primary Minimum Variance base:

- Base Sharpe: `0.4039909849390289`; total turnover: `11.5191438254282`.
- Standard Sentiment Sharpe: `0.3894061998601869`; total turnover:
  `12.046789706438036`.
- Matched-Shrinkage Placebo Sharpe: `0.3952514941026097`; total turnover:
  `11.802349627041298`.
- SignalScope Confidence Lens Sharpe: `0.3918277333346022`; total turnover:
  `11.807426243797446`.

For the Maximum Sharpe robustness base:

- Base Sharpe: `0.4690052735775443`; total turnover: `24.908840121459143`.
- Standard Sentiment Sharpe: `0.4629411494925627`; total turnover:
  `25.058270328965065`.
- Matched-Shrinkage Placebo Sharpe: `0.4655436690259177`; total turnover:
  `24.968792497912368`.
- SignalScope Confidence Lens Sharpe: `0.4617841817789139`; total turnover:
  `25.006839029807654`.

The Standard-to-Confidence turnover reduction is `0.2393634626405916` for
Minimum Variance and `0.0514312991574072` for Maximum Sharpe. The constant
placebo achieves `102.1208820678576%` of the Minimum Variance reduction and
`173.97544397789235%` of the Maximum Sharpe reduction.

## Selectivity Results

`SelectiveDeviation` statistics:

- mean: `0.009414747243539414`
- median: `0.005216118640990201`
- p75: `0.011721398670293676`
- p90: `0.025450950609232453`
- p95: `0.035282647108205625`
- p99: `0.05341067306016963`
- max: `0.0583054117701456`

Confidence is below `C_match` in 148 of 360 observations, or
`0.4111111111111111` of the sample. Confidence is above `C_match` in 212 of 360
observations, or `0.5888888888888889` of the sample.

The four Breadth/Agreement quadrants show that the dynamic rule changes signal
allocation across evidence states:

- High Breadth / High Agreement: average confidence `0.8134443197352658`,
  average absolute placebo tilt `0.0418621576642542`, average absolute
  confidence tilt `0.0537607815709166`.
- High Breadth / Low Agreement: average confidence `0.7419166704838627`,
  average absolute placebo tilt `0.0392398522458698`, average absolute
  confidence tilt `0.0458075561220771`.
- Low Breadth / High Agreement: average confidence `0.4995280474847786`,
  average absolute placebo tilt `0.0570141538255718`, average absolute
  confidence tilt `0.0441807540749358`.
- Low Breadth / Low Agreement: average confidence `0.5800554812636325`,
  average absolute placebo tilt `0.0562129195204185`, average absolute
  confidence tilt `0.0504422838865489`.

The strongest low-confidence attenuation case is Minimum Variance / Utilities on
`2021-06-01`: `z_star = 2.0`, `confidence = 0.3407091184837965`,
`C_match = 0.6322361773345248`, `placebo_multiplier = 1.1264472354669048`,
`confidence_multiplier = 1.0681418236967593`, and `SelectiveDeviation =
0.0583054117701456`.

The strongest high-confidence preservation case in the saved cases is Minimum
Variance / Financials on `2023-09-01`: `z_star = -1.9552305657685027`,
`confidence = 0.8555335717253036`, `C_match = 0.6322361773345248`,
`placebo_multiplier = 0.8763832501290901`, `confidence_multiplier =
0.8327234610521587`, and `SelectiveDeviation = 0.0436597890769315`.

The strongest skeptical counterexample in the saved cases is Minimum Variance /
Comm on `2023-05-01`: `confidence = 0.7088946147144254`, `C_match =
0.6322361773345248`, and `SelectiveDeviation = 0.0075300306107666`. This case
shows that the dynamic rule can be close enough to constant shrinkage that the
extra mechanism may not be economically necessary.

## Findings That Strengthen The Confidence Lens

- The placebo exactly matches the aggregate absolute tilt magnitude, so Phase 2C
  is a stricter test than simply comparing against the unscaled Standard
  Sentiment overlay.
- The Confidence Lens does change which signals are attenuated: 41.1% of
  observations are below `C_match` and 58.9% are above it.
- The quadrant results are economically coherent. High breadth and high
  agreement preserve more signal than the matched placebo, while low-breadth
  states tend to be attenuated more.
- The case table now selects examples without using subsequent returns and
  prefers non-trivial base sector exposure where available.

## Findings That Weaken The Confidence Lens

- The Base portfolio still has the best Sharpe ratio in both Minimum Variance
  and Maximum Sharpe comparisons.
- The matched placebo explains most, and in these artifacts more than all, of
  the Standard-to-Confidence turnover reduction.
- The Confidence Lens does not deliver material performance value beyond the
  matched placebo. In both base methods, the placebo Sharpe is higher than the
  Confidence Lens Sharpe.
- Some skeptical cases show small differences between dynamic confidence and
  constant shrinkage.

## Hypothesis Evaluation

H1: Confidence Lens improves investment performance. `REJECT`.

The Confidence Lens underperforms the Base portfolio on Sharpe for both tested
base methods.

H2: Confidence Lens reduces sentiment-induced portfolio disturbance. `SUPPORT`.

It reduces total turnover relative to Standard Sentiment for both base methods.

H3: Confidence Lens dynamically distinguishes evidence states that a constant
shrinkage rule cannot distinguish. `SUPPORT`.

The aggregate signal budget is matched, but `SelectiveDeviation`, the
below/above-`C_match` split, quadrant results, and cases show that dynamic
confidence reallocates attenuation across evidence states.

H4: Dynamic evidence conditioning is economically necessary. `REJECT`.

The matched placebo explains most of the turnover reduction and performs at
least as well as, and in these artifacts better than, the Confidence Lens on
Sharpe.

## Final Surviving Innovation Claim

The strongest surviving claim is not predictive outperformance. It is that the
SignalScope Confidence Lens is an interpretable, look-ahead-safe, evidence-aware
control layer that changes which sentiment signals are attenuated after matching
aggregate signal strength. It creates defensible diagnostics around when a
headline-sentiment overlay is trusted or muted.

## Strongest Remaining Objection

The strongest remaining objection is that a much simpler constant shrinkage rule
captures most of the portfolio-disturbance benefit and produces better Sharpe in
the saved Phase 2C comparison. That weakens any claim that dynamic evidence
conditioning is economically necessary for this sample.

## Recommendation

Recommendation for the Confidence Lens as the flagship innovation: `REVISE`.

Keep it as the flagship only if the report frames it as an interpretable
falsification-tested risk-control and evidence-diagnostic layer, not as an alpha
engine. Do not claim that it improves investment performance.

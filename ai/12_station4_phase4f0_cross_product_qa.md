# AI Log 12 - Station 4 Phase 4F.0 Cross-Product QA

## Objective

Implement only the final Phase 4F.0 cross-product UI consistency pass for the
approved SignalScope product journey:

`Fund -> Risk -> Signal -> Evidence -> Decision -> Challenge`

No new features, analytics, metrics, backtests, optimisation, sentiment
computation, parameter tuning, deployment work, or report work were added.

No files under `src/` and no saved artifacts under `results/` were modified.

## Human Browser QA Findings

The approved product had a small set of visible consistency issues before
deployment QA:

1. Page navigation and headings sat too close to Streamlit's top chrome and the
   local Deploy toolbar.
2. Decision builder rows gave too much space to `Allocation %` and too little
   to the remove action.
3. Decision remove buttons used `Remove sleeve N`, which could wrap badly.
4. Primary Decision overlap copy mixed integer and one-decimal percentages.
5. Evidence realised allocation-effect bars needed clearer method context for
   the saved attenuation case.
6. Signal gold evidence marks existed but were too subtle in screenshot QA.
7. The final pass needed responsive QA without redesigning approved visuals.

## Global Chrome-Safe Spacing

The old global container rule was:

```css
.block-container {
  padding-top: 1.15rem;
}
```

Phase 4F.0 replaced that with a reusable shell-level spacing token:

```css
--ss-top-safe: clamp(3rem, 5.2vh, 4rem);

.block-container {
  padding-top: calc(var(--ss-top-safe) + env(safe-area-inset-top, 0px));
}
```

A smaller mobile token is applied under `max-width: 760px`:

```css
--ss-top-safe: clamp(2.35rem, 4vh, 3rem);
```

This is one global responsive fix. No page-specific spacer hacks were added and
the Streamlit chrome was not hidden.

## Decision Builder Geometry

Decision builder row columns changed from:

```python
st.columns([1.45, 0.65, 0.42])
```

to:

```python
st.columns([1.7, 0.55, 0.5])
```

This preserves the existing control model while giving the fund selector the
largest width, making `Allocation %` compact, and giving the remove action
enough room to render cleanly.

Allocation logic, validation, duplicate checks, exact-100% requirement, and
normalisation behavior were unchanged.

## Concise Remove Buttons

Visible remove labels changed from:

```text
Remove sleeve 1
Remove sleeve 2
```

to:

```text
Remove
```

Each button keeps its unique Streamlit key:

```python
key=f"remove_decision_sleeve_{index}"
```

## Overlap Precision

The Decision primary narrative previously rounded strongest overlap with zero
decimal places in one location, so a real `83.333%` overlap could display as
`83%`.

Phase 4F.0 uses the existing one-decimal percent convention for primary
Decision overlap copy:

```text
The most overlapping selected pair shares 83.3% of its latest saved
fund-weight profiles.
```

The overlap formula and saved weights were unchanged.

## Evidence Method Context

The underlying RealEstate / 2021-11-01 contradiction had already been fixed
before this pass: the selected saved attenuation case uses saved realised
sector-weight changes from `confidence_lens_attenuation_cases.csv`.

Phase 4F.0 did not rewrite that resolution logic. It added a first-read caption
before the realised bars:

```text
Saved Minimum Variance attenuation case: RealEstate / 2021-11-01.
```

This clarifies that the displayed realised sector allocation changes belong to
the saved Minimum Variance portfolio experiment.

## Signal Evidence Marks

The Signal timeline keeps the approved motif:

- blue continuous signal line;
- gold discrete same-day evidence marks underneath.

The gold evidence layer remains a square point layer, but visibility was
increased modestly:

| Property | Before | After |
|---|---:|---:|
| evidence band height | 38 | 44 |
| mark size | 22 | 34 |
| y placement | 18 | 21 |
| opacity range | 0.12 to 0.95 | 0.28 to 0.95 |

The Signal copy now matches the rendered geometry:

```text
Blue shows sentiment direction. Gold marks underneath show how much same-day
evidence existed for each sector-date.
```

Same-day evidence wording remains separate from trailing B63 Evidence Lens
coverage.

## Protected Product Visuals

The pass did not redesign:

- Fund or Risk;
- Signal selected-date status;
- Evidence Lens;
- Decision Allocation Anatomy;
- Challenge.

The approved Decision structure remains:

```text
FUND WRAPPERS -> LOOK THROUGH -> ASSET CLASSES -> LOOK THROUGH -> UNDERLYING HOLDINGS
```

The approved Decision thesis remains:

```text
FUND COUNT != UNDERLYING DIVERSIFICATION
```

The approved Challenge interpretation, matched-strength equality, direction
aware cases, compact selectivity split, and `REVISE` recommendation remain
unchanged.

## Responsive QA

Browser automation packages were not installed in the local repo environment
(`playwright=False`, `selenium=False`), so Phase 4F.0 used Streamlit AppTest,
static layout inspection, and HTTP smoke.

Inspected by AppTest and static layout checks:

- wide desktop product stages: Fund, Risk, Signal, Evidence, Decision,
  Challenge render without exceptions;
- medium/narrow-sensitive Decision builder controls retain readable labels;
- mobile CSS keeps the global top-safe token smaller than desktop;
- mobile CSS continues stacking metric grids, Evidence Lens rows, Allocation
  Anatomy, Challenge verdicts, split labels, and magnitude rows;
- no new horizontal scrolling wrappers or fixed-position page elements were
  added;
- no letter-by-letter remove labels remain because visible text is now
  `Remove`.

Manual pixel screenshots were not available without adding a browser dependency,
which was intentionally avoided during this frozen UI pass.

## Tests

Focused tests updated:

- `tests/test_app_decision.py`
  - visible remove text is `Remove`;
  - old `Remove sleeve N` visible labels are absent;
  - removal still works with unique keyed buttons;
  - primary overlap narrative displays `83.3%`, not `83%`;
  - Decision look-through calculations remain unchanged.
- `tests/test_app_signal_evidence.py`
  - Signal evidence mark layer remains present;
  - square gold mark size, placement, band height, and opacity range match the
    visibility pass;
  - allocation-effect spec still includes saved realised sector-change labels.
- `tests/test_app_interactions.py`
  - Signal copy uses `Gold marks` and preserves same-day evidence semantics;
  - RealEstate / 2021-11-01 attenuation view identifies the saved Minimum
    Variance case;
  - the exact saved case does not show the unavailable-realised-bars message;
  - global shell spacing uses the top-safe token.

## Verification

Focused app tests:

```text
44 passed in 8.11s
```

Full test suite:

```text
110 passed in 17.65s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Whitespace check:

```text
git diff --check -- .
```

returned no output.

Bounded Streamlit smoke:

```text
HTTP_STATUS=200
```

AppTest render inspection:

```text
apptest_render_inspection_ok Fund,Risk,Signal,Evidence,Decision,Challenge
```

Frozen analytics verification:

```text
git status --short -- src results
```

returned no output.

Runtime dependency scan over `streamlit_app.py app` returned only the approved
denylist occurrence:

```text
app/data.py: Path("results/data/headline_sentiment_scores.csv")
```

No app-layer runtime raw-data loading, `src.data_access`, VADER/NLTK
computation, optimiser, backtest, placebo rebuild, or parameter tuning was
introduced.

## Completion Assessment

Phase 4F.0 is complete for the requested cross-product UI consistency scope.
SignalScope is ready for the next Phase 4F deployment QA step, but deployment
has not been started.

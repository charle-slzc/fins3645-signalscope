# AI Log 14 - Station 4 Phase 4F.2 Live Deployment QA Bugfix

## Objective

Patch only the live-deployment Fund-page selection bug and spacing issues found
after public deployment of SignalScope.

No features were added. No product redesign was performed. No files under
`src/` or `results/` were modified, and no analytical values were changed.

The public Streamlit URL was not supplied in this chat, so this log does not
record or fabricate one.

## Live Issue

Human live QA found that the selected fund dropdown could say one fund while the
risk-return chart continued to highlight and directly label another fund.

Observed live path:

1. Selected fund dropdown showed `Equity / Equal Weight`.
2. The chart correctly highlighted `Equity / Equal Weight`.
3. The dropdown was changed to `Combined / Equal Weight`.
4. The chart still highlighted and labelled `Equity / Equal Weight`.

This was a state-synchronisation defect, not an analytical defect.

## Root Cause

The Fund page read the native Vega selection state from Streamlit session state
before rendering the dropdown controls. Because `st.vega_lite_chart` stores
selection state under its chart key, a previous chart selection could survive a
later dropdown or filter rerun.

That stale chart event could reassert an old fund key before the explicit
dropdown change became the authoritative selection. The result was a split state:
the dropdown showed the newer explicit selection while the chart dataframe and
direct label could still be built from an older selected fund.

Streamlit's chart docs also matter here: chart selection state is returned when
`on_select="rerun"` is used, and a chart key stores the selection state. It is
not a normal mutable app-owned widget value.

## Final State Model

The authoritative selected fund is now the pair:

```text
(selected_fund_family, selected_fund_method)
```

That pair drives:

- selected fund dropdown;
- chart selected flag;
- direct chart label source;
- Risk fact sheet;
- Relative Position;
- Open fact sheet;
- Decision starting fund.

The dropdown label is treated as a widget mirror of that fund key, not as an
independent source of truth.

## Precedence Rule

The Fund page now applies this order in a single render:

1. Family / Method filters define the eligible visible set.
2. If the current selected fund remains eligible, preserve it.
3. If the current selected fund is excluded, choose the first deterministic fund
   from the filtered order and update all selected-fund state.
4. If the dropdown widget already carries a new valid label, treat it as the
   explicit user dropdown action and update the authoritative key.
5. Only after those steps, render the chart.
6. Process a chart click only when no explicit dropdown or filter action occurred
   in the same rerun.

No stale chart selection is allowed to override a newer dropdown or filter
transition.

## Chart-Click Synchronisation

Chart clicks remain supported. A current chart click updates
`selected_fund_family` and `selected_fund_method`, then triggers a rerun. On the
next run, the dropdown label is synced before the selectbox is instantiated.

Explicit dropdown and filter actions also increment the chart widget key version.
That gives the chart a fresh Streamlit identity and prevents old Vega selection
state from being reused after a higher-precedence widget action.

## Filter Transitions

Filter behaviour is now deterministic:

- if the selected fund is still inside the filtered set, it stays selected;
- if the selected fund is no longer eligible, the first valid fund in the
  existing fund order is selected;
- returning filters to `All / All` preserves the current valid selected fund.

Validated transitions include:

- `All / All`, dropdown `Equity / Equal Weight` -> `Combined / Equal Weight`;
- `All / All`, dropdown `Crypto / Equal Weight`;
- `Crypto / Equal Weight` one-result filter;
- `Combined / Maximum Sharpe` one-result filter;
- return to `All / All` with current selection preserved.

## Single-Result Chart Treatment

Single-result filter states now use a deliberate focus mode:

- the selected fund point remains visible;
- axes use padded local domains instead of a visually empty full comparison
  domain;
- copy states: `One fund matches the active filters.`;
- exact annualised return and volatility coordinates are shown next to the chart.

The full nine-fund `All / All` map keeps the approved existing chart behaviour.

Two- and three-result filter states retain the comparative scatter with adaptive
padded axes.

## Spacing Changes

The design system now includes small global spacing tokens:

- micro spacing for captions and labels;
- control spacing for inputs and buttons;
- section spacing for headings and expanders.

The patch adds restrained spacing around:

- widget labels and input borders;
- selectboxes, number inputs, and buttons;
- captions;
- expanders;
- notices and bordered narrative boxes;
- Fund controls and chart focus box.

No page-by-page blank spacer rows were added.

## Tests Added

Regression coverage was added for:

- dropdown `Equity / Equal Weight` -> `Combined / Equal Weight`;
- authoritative selected-fund family/method state;
- Risk fact-sheet target after dropdown selection;
- filter transitions that preserve or replace the selected fund;
- single-result focus mode for `Crypto / Equal Weight`;
- single-result focus mode for `Combined / Maximum Sharpe`;
- return to `All / All` preserving current selected fund;
- chart-click precedence rules;
- chart event parsing updating authoritative fund state;
- chart selected flag and direct-label source using the authoritative key;
- adaptive domains for one-, two-, and three-result states;
- Decision starting fund inheriting current authoritative selection.

## Local Verification

Focused regression suite:

```text
57 passed
```

Full verification is required after this log is created:

```text
python -m pytest -q
python scripts/check_handin.py
git diff --check -- .
git status --short -- src results
```

Bounded Streamlit HTTP smoke and explicit AppTest rendering for Fund, Risk,
Signal, Evidence, Decision, and Challenge are also required.

## Deployment Patch Requirement

This is a deployment patch. After local verification, commit the changed app,
test, and AI-log files and push the standalone `fins3645-signalscope` repository.
Do not push automatically from the AI session without explicit instruction.

## Fund Interaction Simplification and State Red-Team

The first live issue was a split selected-fund state: the visible dropdown could
show one fund while the risk-return map still highlighted and labelled another.
The first patch improved local synchronization but did not solve the hosted
interaction model cleanly enough, because it still kept a dropdown, destructive
filters, adaptive one-result axes, and chart selection state close to the
authoritative app state.

This pass removes the Selected fund dropdown. Family and Method now act only as
focus lenses: they emphasise matching funds while preserving the full nine-fund
risk-return map for context. The map is the primary exploratory fund selector.

The authoritative selected fund remains the app-owned `FundKey` represented by
`selected_fund_family` and `selected_fund_method`. All selected-fund rendering
derives from that identity: the chart selected flag, direct label, selected
context, Relative Position, Open fact sheet, Risk page, and Decision starting
sleeve when Decision has not yet initialized its own allocation state.

The comparison frame is always built from the full `performance_metrics`
universe. It contains nine rows for `All / All`, family focus, method focus, and
unique Family + Method focus. Each row carries `is_selected` and
`is_focus_match`; selected styling wins even when the selected fund is outside
the active focus. Axes use the same full-map domains for every focus state.

Unique focus states select the matching fund deterministically. Multi-match
focus states preserve the current selected fund when it remains in focus;
otherwise they select the first matching fund in the canonical family/method
order. Returning to `All / All` preserves the current valid selected fund.

Vega selection state is now treated only as an input event. A chart click is
converted to `FundKey`, persisted into app-owned state, and followed by a rerun.
The visual highlight after rerun comes from `datum.is_selected`, not from Vega's
selection predicate. A stable event identity is stored after a click is
processed so the same persisted browser event cannot be replayed repeatedly.
Focus-control changes also suppress chart-event processing during that rerun so
a stale map event cannot immediately undo a newly resolved focus selection.

Dead Fund interaction architecture removed in this pass:

- Selected fund dropdown and its label mirror state.
- Dropdown reconciliation and dropdown-precedence rules.
- Filtered chart universe.
- Single-result focus mode and one-point explanatory box.
- Adaptive-axis helper references.
- Interrupted `validate_comparison_frame()` fragment that referenced undefined
  `options` and `filtered`.

Risk continuity remains through the same durable `FundKey` keys. Opening the
fact sheet after selecting `Crypto / Equal Weight` or `Combined / Maximum
Sharpe` through focus lenses lands on the matching Risk fact sheet. Returning
from Risk to Fund preserves the selected point and selected context.

Decision continuity remains intentionally one-way on initialization. If Decision
has no user-edited allocation state, its first sleeve inherits the latest Fund
selection. Once Decision owns `decision_funds` and `decision_allocations`, later
Fund selection changes do not overwrite the user's allocation.

Cross-page state red-team:

- Risk consumes the same durable `FundKey` and has no separate selected-fund
  widget state.
- Signal uses pending/change keys for sector, period, and date updates; curated
  Evidence cases are cleared on manual Signal changes.
- Evidence uses pending context for Signal/Evidence handoff and validates date
  availability when sector/date widgets change.
- Decision owns allocation state after first initialization and validates sleeve
  labels against the saved fund universe.
- Challenge has no persistent interactive selector state beyond navigation.

No high-severity cross-page state defect was found outside Fund during this
pass.

Spacing changes from the earlier live patch were preserved. Removing the
dropdown leaves a compact Fund flow: focus lenses, risk-return map, selected
context with Open fact sheet, then Relative Position. No random blank spacer
rows were added.

Tests updated or added for this pass cover:

- Fresh nine-row comparison frame with the default selected fund highlighted.
- Nine-row map preservation for family, method, and unique focus states.
- Focus-match counts for `All / All`, family lenses, method lenses, and unique
  Family + Method lenses.
- Unique focus auto-selection for `Crypto / Equal Weight` and
  `Combined / Maximum Sharpe`.
- `All / All` preserving the current selected fund.
- Chart event parsing and consumed-event stale protection.
- Selected row and direct-label source deriving from authoritative `FundKey`.
- Open fact sheet and Risk continuity.
- Decision initial inheritance and non-overwrite after user allocation edits.

Local verification for this pass:

```text
python -m pytest -q
121 passed

python scripts/check_handin.py
22 checks passed
1 reminder: no report/report.pdf yet - author it in Word and export to PDF

git diff --check -- fins2026/z5367955_projectB
no output

git status --short -- fins2026/z5367955_projectB/src fins2026/z5367955_projectB/results
no output

bounded Streamlit HTTP smoke
HTTP_STATUS=200

AppTest all six stages
2 passed for explicit all-stage smoke tests
```

Hosted manual verification is still required. Do not claim the hosted
chart-click behavior is fixed until a browser click on the deployed app has
been tested after deployment.

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

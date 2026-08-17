"""SignalScope visual design tokens and Streamlit CSS."""

from __future__ import annotations


APP_TITLE = "SignalScope"
CORE_LINE = "See the signal. Inspect the evidence."
VALUE_PROPOSITION = (
    "Compare the nine investable historical OOS funds, then open a fact sheet to "
    "inspect risk, holdings, concentration, and costs."
)

TRUTH_LABELS = (
    "Historical OOS backtest",
    "Sentiment did not beat Base",
    "No forecast or investment advice",
)

# Locked dark-first semantic tokens. Colours are used for meaning, not decoration.
COLORS = {
    "background": "#0d1412",
    "surface": "#16221e",
    "surface_alt": "#1c2b26",
    "surface_deep": "#101916",
    "text_primary": "#f4f7f2",
    "text_secondary": "#c5d0c9",
    "text_tertiary": "#98a8a0",
    "border": "#30433b",
    "border_soft": "#24362f",
    "action": "#d66f5f",
    "action_dark": "#a94f45",
    "signal": "#7fb7d3",
    "signal_deep": "#2f789a",
    "evidence": "#c8a94f",
    "warning": "#d49a44",
    "negative": "#c85d62",
    "control": "#8f9a96",
    "family_equity": "#84a074",
    "family_crypto": "#b8945a",
    "family_combined": "#6fa7bc",
}


def brand_mark_html() -> str:
    return """
<span class="ss-brand-mark" aria-hidden="true">
  <svg viewBox="0 0 44 28" role="img" focusable="false">
    <path class="ss-mark-scope" d="M5 5H39M5 23H39" />
    <path class="ss-mark-signal" d="M6 16 C12 8 18 19 24 12 S35 11 39 7" />
    <circle class="ss-mark-dot" cx="11" cy="21" r="1.7" />
    <circle class="ss-mark-dot" cx="19" cy="20.5" r="1.7" />
    <circle class="ss-mark-dot" cx="28" cy="21.5" r="1.7" />
    <circle class="ss-mark-dot" cx="36" cy="19.5" r="1.7" />
  </svg>
</span>
"""


def signal_evidence_trace_html() -> str:
    return """
<div class="ss-trace" aria-hidden="true">
  <div class="ss-trace-signal"></div>
  <div class="ss-trace-evidence">
    <span style="left: 9%"></span>
    <span style="left: 31%"></span>
    <span style="left: 57%"></span>
    <span style="left: 82%"></span>
  </div>
</div>
"""


def css() -> str:
    return """
<style>
:root {
  --ss-background: #0d1412;
  --ss-surface: #16221e;
  --ss-surface-alt: #1c2b26;
  --ss-surface-deep: #101916;
  --ss-text-primary: #f4f7f2;
  --ss-text-secondary: #c5d0c9;
  --ss-text-tertiary: #98a8a0;
  --ss-border: #30433b;
  --ss-border-soft: #24362f;
  --ss-action: #d66f5f;
  --ss-action-dark: #a94f45;
  --ss-signal: #7fb7d3;
  --ss-signal-deep: #2f789a;
  --ss-evidence: #c8a94f;
  --ss-warning: #d49a44;
  --ss-negative: #c85d62;
  --ss-control: #8f9a96;
  --ss-family-equity: #84a074;
  --ss-family-crypto: #b8945a;
  --ss-family-combined: #6fa7bc;
  --ss-radius: 8px;
  --ss-space-1: 0.5rem;
  --ss-space-2: 1rem;
  --ss-space-3: 1.5rem;
  --ss-space-5: 2.5rem;
}
.stApp,
[data-testid="stAppViewContainer"] {
  background: var(--ss-background);
  color: var(--ss-text-primary);
}
[data-testid="stHeader"] {
  background: rgba(13, 20, 18, 0.88);
}
.block-container {
  max-width: 78rem;
  padding-top: 1.15rem;
  padding-bottom: 2.5rem;
}
h1, h2, h3, h4, h5, h6,
p, li, label,
[data-testid="stMarkdownContainer"] {
  color: var(--ss-text-primary);
}
[data-testid="stCaptionContainer"],
.stCaption,
small {
  color: var(--ss-text-tertiary) !important;
}
button[kind="primary"] {
  border-color: var(--ss-action) !important;
  background: var(--ss-action) !important;
  color: #101916 !important;
  font-weight: 760 !important;
}
button[kind="secondary"] {
  border-color: var(--ss-border) !important;
  color: var(--ss-text-primary) !important;
  background: var(--ss-surface-alt) !important;
}
[data-testid="stSegmentedControl"] {
  margin: 0 0 var(--ss-space-2);
}
[data-testid="stSegmentedControl"] label {
  color: var(--ss-text-secondary) !important;
}
[data-testid="stSegmentedControl"] button {
  border-color: var(--ss-border) !important;
  color: var(--ss-text-secondary) !important;
  background: var(--ss-surface) !important;
}
[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
  border-color: var(--ss-action) !important;
  color: #101916 !important;
  background: var(--ss-action) !important;
}
[data-baseweb="select"] > div {
  border-color: var(--ss-border) !important;
  background: var(--ss-surface-alt) !important;
  color: var(--ss-text-primary) !important;
}
.stAlert {
  background: var(--ss-surface-alt);
  color: var(--ss-text-primary);
}
.streamlit-expanderHeader {
  color: var(--ss-text-primary) !important;
  background: var(--ss-surface-alt) !important;
  border-color: var(--ss-border) !important;
}
[data-testid="stExpander"] {
  border-color: var(--ss-border) !important;
  background: var(--ss-surface) !important;
}
.signalscope-shell {
  max-width: 70rem;
  margin: 0.15rem 0 var(--ss-space-2);
  padding: var(--ss-space-3);
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius);
  background: linear-gradient(135deg, var(--ss-surface-deep), var(--ss-surface));
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.28);
}
.ss-wordmark {
  display: flex;
  align-items: center;
  gap: 0.62rem;
}
.ss-brand-mark {
  display: inline-flex;
  width: 2.55rem;
  height: 1.65rem;
  flex: 0 0 auto;
}
.ss-brand-mark svg {
  width: 100%;
  height: 100%;
}
.ss-mark-scope {
  fill: none;
  stroke: #687b74;
  stroke-width: 1.15;
}
.ss-mark-signal {
  fill: none;
  stroke: var(--ss-signal);
  stroke-width: 2;
  stroke-linecap: round;
}
.ss-mark-dot {
  fill: var(--ss-evidence);
}
.ss-kicker {
  margin: 0 0 0.28rem;
  color: var(--ss-text-tertiary);
  font-size: 0.74rem;
  font-weight: 740;
  letter-spacing: 0;
  text-transform: uppercase;
}
.ss-hero-title {
  margin: 0;
  color: var(--ss-text-primary);
  font-size: clamp(2rem, 5vw, 3.45rem);
  line-height: 0.98;
  font-weight: 780;
  letter-spacing: 0;
}
.ss-hero-line {
  margin: 0.58rem 0 0;
  color: var(--ss-signal);
  font-size: clamp(1.06rem, 2.2vw, 1.34rem);
  font-weight: 720;
  letter-spacing: 0;
}
.ss-value {
  max-width: 52rem;
  margin: 0.68rem 0 0;
  color: var(--ss-text-secondary);
  font-size: 1rem;
  line-height: 1.5;
}
.ss-trace {
  width: min(12rem, 44%);
  margin: 0.7rem 0 0;
}
.ss-trace-signal {
  height: 0.58rem;
  border-top: 2px solid var(--ss-signal);
  border-radius: 999px;
}
.ss-trace-evidence {
  position: relative;
  height: 0.58rem;
  margin-top: 0.08rem;
}
.ss-trace-evidence span {
  position: absolute;
  top: 0.08rem;
  width: 0.34rem;
  height: 0.34rem;
  border-radius: 999px;
  background: var(--ss-evidence);
}
.ss-label-row {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0;
  margin: 0 0 var(--ss-space-2);
  border-top: 1px solid var(--ss-border);
  border-bottom: 1px solid var(--ss-border);
}
.ss-truth-label {
  display: inline-block;
  padding: 0.38rem 0.68rem;
  border-right: 1px solid var(--ss-border);
  color: var(--ss-text-secondary);
  font-size: 0.8rem;
  font-weight: 680;
}
.ss-truth-label:last-child {
  border-right: 0;
}
.ss-panel {
  min-height: 9rem;
  padding: var(--ss-space-2);
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius);
  background: var(--ss-surface);
}
.ss-panel h3 {
  margin: 0 0 0.45rem;
  color: var(--ss-text-primary);
  font-size: 1rem;
  letter-spacing: 0;
}
.ss-panel p {
  margin: 0;
  color: var(--ss-text-secondary);
  line-height: 1.5;
}
.ss-signal-bar,
.ss-evidence-bar,
.ss-control-bar {
  height: 0.35rem;
  border-radius: 999px;
  margin: 0.8rem 0 0.2rem;
}
.ss-signal-bar {
  background: linear-gradient(90deg, var(--ss-negative), var(--ss-signal), var(--ss-signal-deep));
}
.ss-evidence-bar {
  background: linear-gradient(90deg, #5c4f26, var(--ss-evidence));
}
.ss-control-bar {
  background: linear-gradient(90deg, #4d5854, var(--ss-control));
}
.ss-stage-title {
  margin: 0.25rem 0;
  color: var(--ss-text-primary);
  font-size: clamp(1.45rem, 3.4vw, 2.1rem);
  line-height: 1.12;
  font-weight: 760;
  letter-spacing: 0;
}
.ss-section-label {
  margin: var(--ss-space-3) 0 0.38rem;
  color: var(--ss-text-tertiary);
  font-size: 0.76rem;
  font-weight: 720;
  letter-spacing: 0;
}
.ss-stage-copy {
  max-width: 50rem;
  margin: 0 0 var(--ss-space-2);
  color: var(--ss-text-secondary);
  font-size: 0.98rem;
  line-height: 1.5;
}
.ss-control-frame {
  max-width: 66rem;
  margin: 0.85rem auto var(--ss-space-2);
  padding: 0.85rem 0 0.75rem;
  border-top: 1px solid var(--ss-border);
  border-bottom: 1px solid var(--ss-border);
}
.ss-control-title {
  margin: 0 0 0.5rem;
  color: var(--ss-text-tertiary);
  font-size: 0.76rem;
  font-weight: 720;
  letter-spacing: 0;
}
.ss-chart-frame {
  max-width: 76rem;
  margin: 0 auto;
  padding: 0.65rem 0 0.25rem;
}
.ss-chart-frame canvas,
.ss-chart-frame svg {
  background: transparent !important;
}
.ss-kpi-grid {
  display: grid;
  grid-template-columns: 1.28fr 0.9fr 0.72fr 0.9fr;
  gap: 0.7rem;
  margin: 0.55rem 0 var(--ss-space-2);
}
.ss-kpi {
  padding: 0.9rem;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius);
  background: var(--ss-surface);
}
.ss-kpi.is-primary {
  background: var(--ss-surface-deep);
  border-color: #47615a;
}
.ss-kpi-label {
  margin: 0;
  color: var(--ss-text-tertiary);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0;
}
.ss-kpi-value {
  margin: 0.22rem 0 0;
  color: var(--ss-text-primary);
  font-size: 1.38rem;
  font-weight: 760;
  line-height: 1.05;
}
.ss-kpi.is-primary .ss-kpi-value {
  color: var(--ss-action);
  font-size: clamp(2rem, 4vw, 2.75rem);
}
.ss-kpi-help {
  margin: 0.28rem 0 0;
  color: var(--ss-text-tertiary);
  font-size: 0.77rem;
  line-height: 1.34;
}
.ss-context-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin: 0.45rem 0 0.75rem;
}
.ss-context-item {
  min-width: 8.4rem;
  padding: 0.58rem 0.7rem;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius);
  background: var(--ss-surface-alt);
}
.ss-context-item strong {
  display: block;
  color: var(--ss-text-primary);
  font-size: 0.98rem;
  line-height: 1.1;
}
.ss-context-item span {
  display: block;
  margin-top: 0.15rem;
  color: var(--ss-text-tertiary);
  font-size: 0.75rem;
  line-height: 1.25;
}
.ss-peer-card {
  margin: 0.8rem 0 var(--ss-space-2);
  padding: 0.8rem 0;
  border-top: 1px solid var(--ss-border);
  border-bottom: 1px solid var(--ss-border);
  background: transparent;
}
.ss-peer-title {
  margin: 0 0 0.6rem;
  color: var(--ss-text-primary);
  font-size: 1rem;
  font-weight: 740;
}
.ss-peer-grid {
  display: grid;
  gap: 0.65rem;
}
.ss-relative-line {
  display: grid;
  grid-template-columns: 7rem 1fr 10.25rem;
  gap: 0.75rem;
  align-items: center;
}
.ss-relative-label {
  color: var(--ss-text-primary);
  font-size: 0.86rem;
  font-weight: 740;
}
.ss-relative-track {
  position: relative;
  height: 1.72rem;
}
.ss-relative-track::before {
  content: "";
  position: absolute;
  top: 0.82rem;
  left: 0;
  right: 0;
  height: 1px;
  background: #60736b;
}
.ss-relative-selected,
.ss-relative-median {
  position: absolute;
  transform: translateX(-50%);
}
.ss-relative-selected {
  top: 0.49rem;
  width: 0.76rem;
  height: 0.76rem;
  border: 2px solid var(--ss-text-primary);
  border-radius: 999px;
  background: var(--ss-action);
}
.ss-relative-median {
  top: 0.3rem;
  width: 2px;
  height: 1.1rem;
  background: var(--ss-evidence);
}
.ss-relative-values {
  color: var(--ss-text-secondary);
  font-size: 0.76rem;
  line-height: 1.28;
}
.ss-peer-note {
  margin: 0.35rem 0 0;
  color: var(--ss-text-tertiary);
  font-size: 0.76rem;
  line-height: 1.35;
}
.ss-read-guide,
.ss-holdings-note {
  max-width: 54rem;
  margin: 0.65rem 0 var(--ss-space-2);
  color: var(--ss-text-secondary);
  font-size: 0.9rem;
  line-height: 1.45;
}
.ss-holdings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(17rem, 0.65fr);
  gap: var(--ss-space-3);
  align-items: start;
}
.ss-holdings-context {
  padding-top: 0.1rem;
}
.ss-concentration-flag {
  margin: 0 0 0.65rem;
  padding: 0.78rem 0.85rem;
  border: 1px solid rgba(212, 154, 68, 0.58);
  border-left: 4px solid var(--ss-warning);
  border-radius: var(--ss-radius);
  background: rgba(212, 154, 68, 0.11);
  color: var(--ss-text-primary);
  font-size: 0.9rem;
  line-height: 1.42;
}
.ss-exposure-bar {
  display: flex;
  width: 100%;
  min-height: 3rem;
  overflow: hidden;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius);
  background: var(--ss-surface-deep);
}
.ss-exposure-segment {
  display: flex;
  min-width: 4.85rem;
  align-items: center;
  justify-content: center;
  padding: 0.55rem 0.7rem;
  color: #0d1412;
  font-size: 0.88rem;
  font-weight: 780;
  text-align: center;
}
.ss-exposure-equity {
  background: var(--ss-family-equity);
}
.ss-exposure-crypto {
  background: var(--ss-family-crypto);
}
.ss-single-exposure {
  display: inline-block;
  margin: 0.2rem 0 0.6rem;
  padding: 0.55rem 0;
  border-top: 1px solid var(--ss-border);
  border-bottom: 1px solid var(--ss-border);
  color: var(--ss-text-primary);
  font-size: 1.18rem;
  font-weight: 760;
}
.ss-warning {
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(200, 93, 98, 0.55);
  border-left: 4px solid var(--ss-negative);
  border-radius: var(--ss-radius);
  background: rgba(200, 93, 98, 0.12);
  color: var(--ss-text-primary);
  font-size: 0.9rem;
  line-height: 1.45;
}
.ss-disclosure {
  padding: 0.72rem 0.85rem;
  border: 1px solid var(--ss-border);
  border-left: 4px solid var(--ss-evidence);
  border-radius: var(--ss-radius);
  background: var(--ss-surface-alt);
  color: var(--ss-text-secondary);
  font-size: 0.9rem;
  line-height: 1.45;
}
.ss-method-badge {
  display: inline-flex;
  align-items: center;
  margin: 0 0.45rem 0.45rem 0;
  padding: 0.28rem 0.52rem;
  border: 1px solid var(--ss-border);
  border-radius: 999px;
  background: transparent;
  color: var(--ss-text-secondary);
  font-size: 0.78rem;
  font-weight: 700;
}
@media (max-width: 760px) {
  .block-container {
    padding-left: 1rem;
    padding-right: 1rem;
  }
  .ss-label-row {
    gap: 0.4rem;
  }
  .ss-truth-label {
    border-right: 0;
    border-bottom: 1px solid var(--ss-border);
  }
  .ss-truth-label:last-child {
    border-bottom: 0;
  }
  .ss-kpi-grid {
    grid-template-columns: 1fr 1fr;
  }
  .ss-relative-line,
  .ss-holdings-grid {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }
}
@media (max-width: 520px) {
  .signalscope-shell {
    padding: 1rem;
  }
  .ss-kpi-grid {
    grid-template-columns: 1fr;
  }
  .ss-trace {
    width: 70%;
  }
}
</style>
"""


def truth_label_html(label: str) -> str:
    return f'<span class="ss-truth-label">{label}</span>'

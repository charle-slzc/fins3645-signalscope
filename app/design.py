"""SignalScope visual design tokens and Streamlit CSS."""

from __future__ import annotations


APP_TITLE = "SignalScope"
CORE_LINE = "See the signal. Inspect the evidence."
VALUE_PROPOSITION = (
    "Compare nine systematic funds, inspect risk and holdings, then test whether "
    "news sentiment deserves trust."
)

TRUTH_LABELS = (
    "Historical OOS backtest",
    "Sentiment did not beat Base",
    "No forecast or investment advice",
)

COLORS = {
    "ink": "#17211d",
    "muted": "#5f6d66",
    "paper": "#f7f8f5",
    "panel": "#ffffff",
    "line": "#d8ded7",
    "positive": "#1f7a5c",
    "negative": "#ad3f3f",
    "signal": "#2c6f8f",
    "evidence": "#7b6d2e",
    "control": "#71797a",
}


def css() -> str:
    return """
<style>
:root {
  --ss-ink: #17211d;
  --ss-muted: #5f6d66;
  --ss-paper: #f7f8f5;
  --ss-panel: #ffffff;
  --ss-line: #d8ded7;
  --ss-positive: #1f7a5c;
  --ss-negative: #ad3f3f;
  --ss-signal: #2c6f8f;
  --ss-evidence: #7b6d2e;
  --ss-control: #71797a;
  --ss-shadow: 0 1px 2px rgba(23, 33, 29, 0.06);
}
.signalscope-shell {
  color: var(--ss-ink);
}
.ss-kicker {
  margin: 0 0 0.35rem;
  color: var(--ss-muted);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}
.ss-hero-title {
  margin: 0;
  color: var(--ss-ink);
  font-size: clamp(2.4rem, 7vw, 4.6rem);
  line-height: 0.98;
  font-weight: 760;
  letter-spacing: 0;
}
.ss-hero-line {
  margin: 0.75rem 0 0;
  color: var(--ss-signal);
  font-size: clamp(1.15rem, 2.4vw, 1.55rem);
  font-weight: 700;
  letter-spacing: 0;
}
.ss-value {
  max-width: 58rem;
  margin: 0.85rem 0 0;
  color: var(--ss-muted);
  font-size: 1.06rem;
  line-height: 1.55;
}
.ss-label-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin: 1.2rem 0 1.4rem;
}
.ss-truth-label {
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  padding: 0.35rem 0.65rem;
  border: 1px solid var(--ss-line);
  border-radius: 999px;
  background: var(--ss-panel);
  color: var(--ss-ink);
  font-size: 0.88rem;
  box-shadow: var(--ss-shadow);
}
.ss-panel {
  min-height: 11rem;
  padding: 1.1rem;
  border: 1px solid var(--ss-line);
  border-radius: 8px;
  background: var(--ss-panel);
  box-shadow: var(--ss-shadow);
}
.ss-panel h3 {
  margin: 0 0 0.45rem;
  color: var(--ss-ink);
  font-size: 1.05rem;
  letter-spacing: 0;
}
.ss-panel p {
  margin: 0;
  color: var(--ss-muted);
  line-height: 1.5;
}
.ss-structure-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.ss-signal-bar,
.ss-evidence-bar,
.ss-control-bar {
  height: 0.45rem;
  border-radius: 999px;
  margin: 0.9rem 0 0.3rem;
}
.ss-signal-bar {
  background: linear-gradient(90deg, var(--ss-negative), #edf0ed, var(--ss-positive));
}
.ss-evidence-bar {
  background: linear-gradient(90deg, #ece7cf, var(--ss-evidence));
}
.ss-control-bar {
  background: linear-gradient(90deg, #e8ebea, var(--ss-control));
}
.ss-small {
  color: var(--ss-muted);
  font-size: 0.86rem;
  line-height: 1.45;
}
.ss-stage-title {
  margin: 0.4rem 0 0.3rem;
  color: var(--ss-ink);
  font-size: clamp(1.6rem, 4vw, 2.35rem);
  line-height: 1.1;
  font-weight: 740;
  letter-spacing: 0;
}
.ss-stage-copy {
  max-width: 52rem;
  margin: 0 0 1rem;
  color: var(--ss-muted);
  font-size: 1rem;
  line-height: 1.55;
}
.ss-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  align-items: center;
  margin: 0.8rem 0 1rem;
}
.ss-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.7rem;
  margin: 1rem 0 1.1rem;
}
.ss-kpi {
  padding: 0.85rem;
  border: 1px solid var(--ss-line);
  border-radius: 8px;
  background: var(--ss-panel);
  box-shadow: var(--ss-shadow);
}
.ss-kpi-label {
  margin: 0;
  color: var(--ss-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}
.ss-kpi-value {
  margin: 0.22rem 0 0;
  color: var(--ss-ink);
  font-size: 1.45rem;
  font-weight: 760;
  line-height: 1.05;
}
.ss-kpi-help {
  margin: 0.25rem 0 0;
  color: var(--ss-muted);
  font-size: 0.78rem;
  line-height: 1.35;
}
.ss-mini-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0.7rem 0 1rem;
}
.ss-mini {
  padding: 0.75rem;
  border: 1px solid var(--ss-line);
  border-radius: 8px;
  background: var(--ss-panel);
}
.ss-mini strong {
  display: block;
  color: var(--ss-ink);
  font-size: 1.1rem;
}
.ss-mini span {
  display: block;
  color: var(--ss-muted);
  font-size: 0.8rem;
  line-height: 1.35;
}
.ss-caveat {
  padding: 0.75rem 0.85rem;
  border-left: 4px solid var(--ss-evidence);
  border-radius: 8px;
  background: #fbfaf2;
  color: var(--ss-ink);
  font-size: 0.9rem;
  line-height: 1.45;
}
.ss-warning {
  padding: 0.75rem 0.85rem;
  border-left: 4px solid var(--ss-negative);
  border-radius: 8px;
  background: #fff7f6;
  color: var(--ss-ink);
  font-size: 0.9rem;
  line-height: 1.45;
}
.ss-method-badge {
  display: inline-flex;
  align-items: center;
  margin: 0 0.45rem 0.45rem 0;
  padding: 0.28rem 0.55rem;
  border: 1px solid var(--ss-line);
  border-radius: 999px;
  background: var(--ss-panel);
  color: var(--ss-muted);
  font-size: 0.78rem;
  font-weight: 700;
}
.ss-fund-row {
  display: grid;
  grid-template-columns: minmax(11rem, 1.2fr) repeat(5, minmax(5.5rem, 0.8fr));
  gap: 0.55rem;
  align-items: center;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--ss-line);
  color: var(--ss-ink);
  font-size: 0.88rem;
}
.ss-fund-row span {
  color: var(--ss-muted);
}
@media (max-width: 760px) {
  .ss-structure-grid {
    grid-template-columns: 1fr;
  }
  .ss-panel {
    min-height: auto;
  }
  .ss-label-row {
    gap: 0.45rem;
  }
  .ss-truth-label {
    width: 100%;
    justify-content: center;
  }
  .ss-kpi-grid,
  .ss-mini-grid {
    grid-template-columns: 1fr 1fr;
  }
  .ss-fund-row {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 520px) {
  .ss-kpi-grid,
  .ss-mini-grid,
  .ss-fund-row {
    grid-template-columns: 1fr;
  }
}
</style>
"""


def truth_label_html(label: str) -> str:
    return f'<span class="ss-truth-label">{label}</span>'

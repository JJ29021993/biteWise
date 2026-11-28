"""Streamlit UI for the restaurant recommendation pipeline (Phase 5).

Cinematic Epicurean dark theme aligned with Stitch BiteWise mocks.

Run:
    streamlit run src/ui/app.py
"""

from __future__ import annotations

import streamlit as st

from src.filtering.preferences import PreferenceValidationError
from src.services import RecommendationResponse, RecommenderService, recommend
from src.services.models import RecommendationItem
from src.ui.options import default_location_index, get_cuisine_options, get_location_options
from src.ui.render import (
    empty_state_html,
    idle_panel_html,
    loading_skeleton_html,
    meta_pills_html,
    recommendation_card_html,
    summary_banner_html,
)

_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root {
  --bw-canvas: #0e0f12;
  --bw-surface: #171a1f;
  --bw-surface-2: #1f1f23;
  --bw-surface-3: #20242b;
  --bw-surface-high: #292a2d;
  --bw-stroke: #2a2f38;
  --bw-stroke-hot: #3b424f;
  --bw-crimson: #e23744;
  --bw-crimson-deep: #cb202d;
  --bw-crimson-bright: #ff535a;
  --bw-ink: #f4f4f5;
  --bw-muted: #9aa0a6;
  --bw-disabled: #4b5362;
  --bw-glow: rgba(226, 55, 68, 0.12);
  --bw-rating-high: #22c55e;
  --bw-rating-mid: #eab308;
  --bw-rating-low: #f97316;
  --bw-tertiary: #4ae176;
  --bw-focus: #e23744;
  --bw-radius: 16px;
}

html, body, [class*="css"] {
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
  color: var(--bw-ink);
  color-scheme: dark;
}

.stApp {
  background:
    radial-gradient(ellipse 80% 50% at 50% -8%, rgba(226, 55, 68, 0.14), transparent 70%),
    radial-gradient(ellipse 40% 30% at 90% 20%, rgba(0, 167, 75, 0.05), transparent 60%),
    var(--bw-canvas) !important;
  color: var(--bw-ink);
}
.stApp > header,
[data-testid="stHeader"] {
  background: transparent !important;
}
section[data-testid="stSidebar"] {
  background: var(--bw-surface) !important;
  border-right: 1px solid var(--bw-stroke);
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
  color: var(--bw-ink) !important;
}
.block-container {
  padding-top: 1.25rem;
  padding-bottom: 2.5rem;
  max-width: 1180px;
}

h1, h2, h3, .bw-brand, .bw-panel-title, .bw-name, .bw-idle-title, .bw-empty-title {
  font-family: Outfit, "Source Sans 3", sans-serif !important;
  letter-spacing: -0.02em;
  color: var(--bw-ink) !important;
}

/* —— Top chrome —— */
.bw-topbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1rem;
  margin: 0 0 1.25rem 0;
  padding: 0.85rem 1rem;
  border-radius: 14px;
  background: rgba(13, 14, 17, 0.85);
  border: 1px solid var(--bw-stroke);
  backdrop-filter: blur(12px);
}
.bw-topbar-brand {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem 0.75rem;
}
.bw-brand {
  font-size: 1.45rem;
  font-weight: 700;
  margin: 0;
  color: #ffb3b1 !important;
  line-height: 1.1;
}
.bw-brand-dot {
  color: var(--bw-crimson-bright);
}
.bw-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: var(--bw-surface-high);
  color: #e4bebc;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.bw-micro {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.28rem 0.65rem;
  border-radius: 999px;
  background: var(--bw-surface-2);
  color: var(--bw-ink);
  font-size: 0.78rem;
  font-weight: 600;
  border: 1px solid transparent;
}
.bw-micro-muted {
  background: var(--bw-surface);
  color: var(--bw-muted);
}
.bw-status-ready {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  background: rgba(0, 167, 75, 0.18);
  color: var(--bw-tertiary);
  font-size: 0.72rem;
  font-weight: 700;
}
.bw-status-ready::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--bw-tertiary);
  box-shadow: 0 0 0 3px rgba(74, 225, 118, 0.2);
  animation: bw-pulse 1.6s ease-in-out infinite;
}

/* —— Hero —— */
.bw-hero {
  position: relative;
  overflow: hidden;
  padding: 1.5rem 1.5rem 1.55rem;
  margin: 0 0 1.35rem 0;
  border-radius: var(--bw-radius);
  background: var(--bw-surface);
  border: 1px solid var(--bw-stroke);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}
.bw-hero::before {
  content: "";
  position: absolute;
  right: -6rem;
  top: -6rem;
  width: 18rem;
  height: 18rem;
  border-radius: 50%;
  background: rgba(255, 83, 90, 0.1);
  filter: blur(48px);
  pointer-events: none;
}
.bw-hero-inner {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
}
.bw-kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0 0 0.45rem 0;
  color: var(--bw-crimson-bright);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.bw-kicker::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--bw-crimson-bright);
  animation: bw-pulse 1.4s ease-in-out infinite;
}
.bw-hero-title {
  font-family: Outfit, sans-serif;
  font-size: clamp(2rem, 4vw, 2.75rem);
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.03em;
  color: var(--bw-ink) !important;
  line-height: 1.1;
}
.bw-tagline {
  color: #e4bebc;
  font-size: 1.05rem;
  margin: 0.55rem 0 0 0;
  max-width: 34rem;
  line-height: 1.5;
  font-weight: 400;
}
.bw-hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.bw-hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  background: var(--bw-surface-2);
  border: 1px solid var(--bw-stroke);
  color: var(--bw-ink);
  font-size: 0.82rem;
  font-weight: 600;
}

.bw-panel-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 0.25rem 0;
}
.bw-panel-sub {
  color: var(--bw-muted) !important;
  font-size: 0.9rem;
  margin: 0 0 0.85rem 0;
}

/* —— Result cards —— */
.bw-card {
  background: var(--bw-surface-2);
  border: 1px solid var(--bw-stroke);
  border-radius: var(--bw-radius);
  overflow: hidden;
  margin-bottom: 1rem;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}
.bw-card:hover {
  transform: translateY(-2px);
  border-color: var(--bw-stroke-hot);
  box-shadow: 0 14px 36px -6px rgba(0, 0, 0, 0.55);
}
.bw-card-banner {
  padding: 0.95rem 1.1rem 0.85rem;
  background:
    linear-gradient(135deg, rgba(226, 55, 68, 0.18) 0%, transparent 55%),
    linear-gradient(180deg, #292a2d 0%, #1b1b1f 100%);
  border-bottom: 1px solid var(--bw-stroke);
}
.bw-card-banner-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.bw-pick {
  display: inline-flex;
  align-items: center;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  background: var(--bw-crimson-bright);
  color: #5b000e;
  font-size: 0.78rem;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(226, 55, 68, 0.35);
}
.bw-card-geo {
  margin: 0.65rem 0 0 0;
  color: rgba(244, 244, 245, 0.85);
  font-size: 0.8rem;
  font-weight: 600;
}
.bw-card-body {
  padding: 1rem 1.1rem 1.1rem;
}
.bw-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}
.bw-card-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}
.bw-rank {
  flex: 0 0 auto;
  font-family: Outfit, sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--bw-crimson-bright);
}
.bw-name {
  font-size: 1.28rem;
  font-weight: 700;
  margin: 0;
  color: var(--bw-ink) !important;
  line-height: 1.25;
}
.bw-cost-block {
  text-align: right;
  flex: 0 0 auto;
}
.bw-cost-label {
  display: block;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--bw-muted);
}
.bw-cost-value {
  font-family: Outfit, sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--bw-crimson-bright);
}
.bw-rating {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  min-width: 3.2rem;
  height: 1.75rem;
  padding: 0 0.55rem;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.88rem;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  backdrop-filter: blur(8px);
}
.bw-rating-star {
  font-size: 0.72rem;
  line-height: 1;
  margin-top: -1px;
}
.bw-rating-value {
  font-family: Outfit, "Source Sans 3", sans-serif;
  letter-spacing: 0.01em;
}
.bw-rating-high {
  color: var(--bw-rating-high);
  background: rgba(34, 197, 94, 0.16);
  border: 1px solid rgba(34, 197, 94, 0.3);
}
.bw-rating-mid {
  color: var(--bw-rating-mid);
  background: rgba(234, 179, 8, 0.16);
  border: 1px solid rgba(234, 179, 8, 0.3);
}
.bw-rating-low {
  color: var(--bw-rating-low);
  background: rgba(249, 115, 22, 0.16);
  border: 1px solid rgba(249, 115, 22, 0.3);
}
.bw-rating-na {
  color: var(--bw-muted);
  background: rgba(155, 160, 166, 0.14);
  border: 1px solid rgba(155, 160, 166, 0.25);
  min-width: 2.4rem;
}
.bw-submeta {
  color: var(--bw-muted);
  font-size: 0.92rem;
  margin: 0.4rem 0 0.65rem 0;
  line-height: 1.45;
}
.bw-dot {
  margin: 0 0.28rem;
  opacity: 0.7;
}
.bw-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
}
.bw-chip {
  display: inline-flex;
  padding: 0.2rem 0.55rem;
  border-radius: 8px;
  background: var(--bw-surface-high);
  color: var(--bw-ink);
  font-size: 0.72rem;
  font-weight: 600;
}
.bw-insight {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.75rem 0.85rem;
  border-radius: 12px;
  background: rgba(226, 55, 68, 0.08);
  border-left: 3px solid var(--bw-crimson);
}
.bw-insight-icon {
  flex: 0 0 auto;
  color: var(--bw-crimson-bright);
  font-size: 0.95rem;
  margin-top: 0.1rem;
}
.bw-explain {
  color: var(--bw-ink);
  line-height: 1.55;
  margin: 0;
  font-size: 0.94rem;
}

.bw-pill {
  display: inline-block;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 650;
  background: rgba(226, 55, 68, 0.12);
  color: #ffb3b1;
  border: 1px solid rgba(226, 55, 68, 0.35);
  margin: 0.15rem 0.35rem 0.35rem 0;
}
.bw-summary {
  background: rgba(226, 55, 68, 0.06);
  border: 1px solid rgba(226, 55, 68, 0.28);
  border-left: 3px solid var(--bw-crimson);
  padding: 0.95rem 1.05rem;
  margin: 0.55rem 0 1rem 0;
  border-radius: 0 12px 12px 0;
  line-height: 1.55;
  color: var(--bw-ink);
}
.bw-summary-kicker {
  display: block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--bw-crimson-bright);
  margin-bottom: 0.35rem;
}
.bw-summary p {
  margin: 0;
  color: var(--bw-ink) !important;
}

/* —— Idle / empty / loading —— */
.bw-idle, .bw-empty {
  position: relative;
  overflow: hidden;
  text-align: center;
  padding: 2.25rem 1.5rem 1.75rem;
  border-radius: var(--bw-radius);
  background: var(--bw-surface-2);
  border: 1px solid var(--bw-stroke);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.35);
}
.bw-idle::before, .bw-empty::before {
  content: "";
  position: absolute;
  width: 14rem;
  height: 14rem;
  top: 15%;
  left: 50%;
  transform: translateX(-50%);
  border-radius: 50%;
  background: rgba(177, 2, 30, 0.12);
  filter: blur(40px);
  pointer-events: none;
}
.bw-idle-icon {
  position: relative;
  z-index: 1;
  width: 4.5rem;
  height: 4.5rem;
  margin: 0 auto 1rem;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--bw-surface-high);
  color: var(--bw-crimson-bright);
  font-size: 1.85rem;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
}
.bw-idle-title, .bw-empty-title {
  position: relative;
  z-index: 1;
  font-size: clamp(1.45rem, 2.5vw, 1.85rem);
  font-weight: 700;
  margin: 0 0 0.55rem 0;
}
.bw-idle-copy, .bw-empty-copy, .bw-empty-hint {
  position: relative;
  z-index: 1;
  color: var(--bw-muted) !important;
  max-width: 32rem;
  margin: 0 auto 1.1rem;
  line-height: 1.55;
  font-size: 0.98rem;
}
.bw-idle-presets {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}
.bw-preset {
  padding: 0.45rem 0.85rem;
  border-radius: 10px;
  background: var(--bw-surface-high);
  border: 1px solid var(--bw-stroke);
  color: var(--bw-ink);
  font-size: 0.82rem;
  font-weight: 600;
}
.bw-idle-trust {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0;
  padding: 0.45rem 0.85rem;
  border-radius: 999px;
  background: rgba(0, 167, 75, 0.12);
  color: var(--bw-tertiary) !important;
  font-size: 0.78rem;
  font-weight: 600;
}
.bw-idle-trust-mark {
  display: inline-grid;
  place-items: center;
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 50%;
  background: rgba(74, 225, 118, 0.25);
  font-size: 0.7rem;
}
.bw-empty-badge {
  position: relative;
  z-index: 1;
  display: inline-flex;
  margin-bottom: 0.75rem;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  background: rgba(226, 55, 68, 0.15);
  border: 1px solid rgba(226, 55, 68, 0.4);
  color: #ffb3b1;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.bw-loading {
  padding: 1.1rem;
  border-radius: var(--bw-radius);
  background: var(--bw-surface-2);
  border: 1px solid var(--bw-stroke);
}
.bw-loading-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
.bw-loading-kicker {
  margin: 0;
  font-family: Outfit, sans-serif;
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--bw-ink);
}
.bw-loading-copy {
  margin: 0.25rem 0 0;
  color: var(--bw-muted);
  font-size: 0.9rem;
}
.bw-loading-pct {
  flex: 0 0 auto;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  background: rgba(0, 167, 75, 0.15);
  color: var(--bw-tertiary);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.bw-loading-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 1rem;
}
.bw-step {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.7rem;
  border-radius: 10px;
  background: var(--bw-surface);
  border: 1px solid var(--bw-stroke);
  color: var(--bw-muted);
  font-size: 0.78rem;
  font-weight: 600;
}
.bw-step-done {
  color: var(--bw-tertiary);
  border-color: rgba(74, 225, 118, 0.3);
  background: rgba(0, 167, 75, 0.1);
}
.bw-step-active {
  color: #ffb3b1;
  border-color: rgba(226, 55, 68, 0.4);
  background: rgba(226, 55, 68, 0.1);
}
.bw-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--bw-crimson-bright);
  animation: bw-pulse 1.1s ease-in-out infinite;
}
.bw-skel-card {
  margin-bottom: 0.75rem;
  padding: 0.85rem;
  border-radius: 14px;
  background: var(--bw-surface);
  border: 1px solid var(--bw-stroke);
}
.bw-skel-card.dim { opacity: 0.55; }
.bw-skel-banner {
  height: 4.5rem;
  border-radius: 10px;
  margin-bottom: 0.75rem;
  background: linear-gradient(90deg, #292a2d 0%, #343538 50%, #292a2d 100%);
  background-size: 200% 100%;
  animation: bw-shimmer 1.4s linear infinite;
}
.bw-skel-line {
  height: 0.7rem;
  border-radius: 6px;
  margin-bottom: 0.45rem;
  background: linear-gradient(90deg, #292a2d 0%, #343538 50%, #292a2d 100%);
  background-size: 200% 100%;
  animation: bw-shimmer 1.4s linear infinite;
}
.bw-skel-line.w50 { width: 50%; }
.bw-skel-line.w55 { width: 55%; }
.bw-skel-line.w60 { width: 60%; }
.bw-skel-line.w70 { width: 70%; }
.bw-skel-line.w75 { width: 75%; }
.bw-skel-line.w80 { width: 80%; }
.bw-skel-line.w85 { width: 85%; }
.bw-skel-line.w90 { width: 90%; }

.bw-footer {
  margin-top: 1.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--bw-stroke);
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  color: var(--bw-muted);
  font-size: 0.78rem;
}
.bw-footer strong {
  color: var(--bw-ink);
  font-weight: 600;
}

/* —— Streamlit widget chrome —— */
div[data-testid="stForm"] {
  background: var(--bw-surface-2);
  border: 1px solid var(--bw-stroke);
  border-radius: var(--bw-radius);
  padding: 1.05rem 1.1rem 0.65rem;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.35);
}

label, p, .stMarkdown, .stText, [data-testid="stWidgetLabel"] {
  color: var(--bw-ink) !important;
}
.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--bw-muted) !important;
}

div[data-baseweb="input"],
div[data-baseweb="textarea"],
div[data-baseweb="select"] > div {
  background-color: var(--bw-surface-high) !important;
  border-color: var(--bw-stroke) !important;
  border-radius: 10px !important;
  color: var(--bw-ink) !important;
}
input, textarea, select {
  color: var(--bw-ink) !important;
  caret-color: var(--bw-ink);
}
div[data-baseweb="select"] span,
div[data-baseweb="tag"] {
  color: var(--bw-ink) !important;
}
div[data-baseweb="tag"] {
  background: rgba(177, 2, 30, 0.35) !important;
  border-color: rgba(226, 55, 68, 0.35) !important;
}

.stSlider [data-baseweb="slider"] div[role="slider"] {
  background-color: var(--bw-crimson-bright) !important;
}
.stMultiSelect [data-baseweb="select"] {
  background: transparent !important;
}

.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(180deg, #ff535a 0%, var(--bw-crimson) 100%) !important;
  color: #5b000e !important;
  border: none !important;
  font-weight: 700 !important;
  border-radius: 12px !important;
  box-shadow: 0 8px 22px rgba(226, 55, 68, 0.35);
}
.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  filter: brightness(1.08);
  box-shadow: 0 10px 28px rgba(226, 55, 68, 0.45);
}

div[data-testid="stAlert"] {
  border-radius: 12px;
  border: 1px solid var(--bw-stroke);
  background: var(--bw-surface) !important;
}

button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
[tabindex]:focus-visible {
  outline: 3px solid rgba(226, 55, 68, 0.55) !important;
  outline-offset: 2px !important;
}

@keyframes bw-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.55; transform: scale(0.85); }
}
@keyframes bw-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
  .bw-card:hover { transform: none; }
  .bw-status-ready::before, .bw-kicker::before { animation: none !important; }
}
</style>
"""


def render_recommendation_card(item: RecommendationItem) -> None:
    st.markdown(
        recommendation_card_html(
            rank=item.rank,
            name=item.name,
            cuisine=item.cuisine,
            rating=item.rating,
            estimated_cost=item.estimated_cost,
            location=item.location,
            explanation=item.explanation,
        ),
        unsafe_allow_html=True,
    )


def render_meta_banners(response: RecommendationResponse) -> None:
    meta = response.meta
    if meta.error:
        st.error("Something went wrong while generating recommendations. Please try again.")
        return

    if meta.relaxed and meta.filters_relaxed:
        relaxed = ", ".join(meta.filters_relaxed)
        st.warning(
            f"Constraint boundary reached — relaxed: **{relaxed}**. "
            "Location was kept. Try a nearby area or a wider budget."
        )

    if meta.llm_fallback:
        st.info(
            "AI ranking was unavailable, so results are sorted by rating/cost. "
            "Restaurant facts below are still from the dataset."
        )

    if meta.dry_run:
        st.caption("Dry-run mode: mock explanations (no live LLM call).")

    chips = [f"{meta.candidates_considered} places matched"]
    if meta.filters_applied:
        chips.append("filters: " + ", ".join(meta.filters_applied))
    st.markdown(meta_pills_html(chips), unsafe_allow_html=True)


def render_results(response: RecommendationResponse) -> None:
    render_meta_banners(response)

    if response.meta.error:
        return

    if response.is_empty:
        reason = response.meta.empty_reason or "No restaurants matched your preferences."
        st.markdown(empty_state_html(reason), unsafe_allow_html=True)
        return

    if response.summary:
        st.markdown(summary_banner_html(response.summary), unsafe_allow_html=True)

    st.markdown(
        f'<p class="bw-panel-title">{len(response.recommendations)} restaurants for you</p>',
        unsafe_allow_html=True,
    )
    for item in response.recommendations:
        render_recommendation_card(item)


@st.cache_resource(show_spinner=False)
def get_service() -> RecommenderService:
    """Process-wide service with cached restaurant store."""
    return RecommenderService()


@st.cache_data(show_spinner=False)
def load_ui_options() -> tuple[list[str], list[str]]:
    return get_location_options(), get_cuisine_options()


def _render_chrome() -> None:
    st.markdown(
        """
        <div class="bw-topbar" role="banner">
          <div class="bw-topbar-brand">
            <p class="bw-brand">BiteWise<span class="bw-brand-dot">.</span></p>
            <span class="bw-badge">AI Curated</span>
            <span class="bw-micro">Bangalore</span>
            <span class="bw-micro bw-micro-muted">Zomato Verified</span>
          </div>
          <div class="bw-status-ready">AI Shortlist Ready</div>
        </div>
        <header class="bw-hero">
          <div class="bw-hero-inner">
            <div>
              <p class="bw-kicker">Neural Engine</p>
              <h1 class="bw-hero-title">BiteWise<span class="bw-brand-dot">.</span></h1>
              <p class="bw-tagline">Discover restaurants that match your taste</p>
            </div>
            <div class="bw-hero-pills" aria-hidden="true">
              <span class="bw-hero-pill">Bangalore</span>
              <span class="bw-hero-pill">Zomato listings</span>
              <span class="bw-hero-pill">AI shortlist</span>
            </div>
          </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def _render_footer() -> None:
    st.markdown(
        """
        <footer class="bw-footer">
          <span><strong>BiteWise</strong> · Bangalore culinary intelligence</span>
          <span>Live data sync via Zomato · Zero ads · No sponsored placements</span>
        </footer>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="BiteWise · Discover restaurants",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    _render_chrome()

    with st.sidebar:
        st.header("How it works")
        st.markdown(
            "1. Hard filters narrow candidates  \n"
            "2. Groq ranks and explains the shortlist  \n"
            "3. Facts (name, rating, cost) always come from the dataset"
        )
        dry_run = st.toggle(
            "Dry-run / offline test mode",
            value=False,
            help="Skip live Groq calls. Useful for UI demos without API spend.",
        )
        st.caption("Needs GROQ_API_KEY in .env when dry-run is off.")

    try:
        locations, cuisines = load_ui_options()
    except FileNotFoundError:
        st.error(
            "Processed restaurant data is missing. "
            "Run `python -m src.ingestion` from the project root, then refresh."
        )
        return

    left, right = st.columns([0.92, 1.28], gap="large")

    with left:
        st.markdown(
            '<p class="bw-panel-title">Set Your Taste Profile</p>'
            '<p class="bw-panel-sub">Facts from Zomato listings, ranking by AI</p>',
            unsafe_allow_html=True,
        )
        with st.form("preferences_form", clear_on_submit=False):
            location = st.selectbox(
                "Neighborhood",
                options=locations,
                index=default_location_index(locations),
                help="Neighborhood or city-wide Bangalore search.",
            )
            budget = st.selectbox(
                "Budget Band",
                options=["low", "medium", "high"],
                index=1,
                format_func=lambda b: {
                    "low": "Low",
                    "medium": "Medium",
                    "high": "High",
                }[b],
                help="Mapped to cost-for-two ranges from the dataset.",
            )
            cuisine_selected = st.multiselect(
                "Preferred Cuisines",
                options=cuisines,
                default=[],
                help="Leave empty for any cuisine. Multiple values use OR matching.",
                placeholder="Any cuisine",
            )
            min_rating = st.slider(
                "Minimum Rating",
                min_value=0.0,
                max_value=5.0,
                value=4.0,
                step=0.1,
            )
            additional = st.text_area(
                "Sensory & Ambiance Notes",
                value="",
                placeholder="quiet corner, outdoor seating, authentic pasta, date night…",
                height=90,
            )
            top_k = st.slider(
                "Target Shortlist",
                min_value=1,
                max_value=10,
                value=5,
            )
            submitted = st.form_submit_button(
                "Find restaurants",
                type="primary",
                use_container_width=True,
            )

    with right:
        st.markdown(
            '<p class="bw-panel-title">Recommendations</p>'
            '<p class="bw-panel-sub">AI-ranked shortlist with grounded explanations</p>',
            unsafe_allow_html=True,
        )
        if not submitted:
            st.markdown(idle_panel_html(), unsafe_allow_html=True)
            _render_footer()
            return

        if not str(location).strip():
            st.error("Location is required.")
            _render_footer()
            return

        cuisine_value = ", ".join(cuisine_selected) if cuisine_selected else None
        payload = {
            "location": str(location).strip(),
            "budget": budget,
            "cuisine": cuisine_value,
            "min_rating": float(min_rating),
            "additional_preferences": additional.strip() or None,
            "top_k": int(top_k),
        }

        try:
            get_service()
            skeleton = st.empty()
            skeleton.markdown(loading_skeleton_html(), unsafe_allow_html=True)
            with st.spinner("Ranking restaurants…"):
                response = recommend(payload, dry_run=dry_run)
            skeleton.empty()
        except PreferenceValidationError as exc:
            st.error(f"Please check your preferences: {exc}")
            _render_footer()
            return
        except FileNotFoundError:
            st.error(
                "Processed restaurant data is missing. "
                "Run `python -m src.ingestion` from the project root, then retry."
            )
            _render_footer()
            return
        except Exception:  # noqa: BLE001 - keep UI alive (U07)
            st.error(
                "Unexpected error while recommending. "
                "The app is still usable — try again."
            )
            _render_footer()
            return

        render_results(response)

    _render_footer()


if __name__ == "__main__":
    main()

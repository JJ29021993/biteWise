"""Pure rendering helpers for the Streamlit UI (no Streamlit imports)."""

from __future__ import annotations

import html
from typing import Any


def escape_html(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def clamp_explanation(text: str | None, limit: int = 420) -> str:
    """UI-friendly explanation with a soft length cap (U08)."""
    if not text:
        return "Recommended based on your filters."
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def format_rating(rating: float | None) -> str:
    if rating is None:
        return "—"
    try:
        return f"{float(rating):.1f}"
    except (TypeError, ValueError):
        return "—"


def rating_badge_class(rating: float | None) -> str:
    """Semantic rating color bands (Cinematic Epicurean tiers)."""
    if rating is None:
        return "bw-rating bw-rating-na"
    try:
        value = float(rating)
    except (TypeError, ValueError):
        return "bw-rating bw-rating-na"
    if value >= 4.0:
        return "bw-rating bw-rating-high"
    if value >= 3.0:
        return "bw-rating bw-rating-mid"
    if value > 0:
        return "bw-rating bw-rating-low"
    return "bw-rating bw-rating-na"


def rating_badge_html(rating: float | None) -> str:
    """Compact rating chip with star + score."""
    rating_text = format_rating(rating)
    badge = rating_badge_class(rating)
    if rating is None:
        return (
            f'<span class="{badge}" title="Rating unavailable" aria-label="Rating unavailable">'
            f'<span class="bw-rating-value">{escape_html(rating_text)}</span>'
            f"</span>"
        )
    return (
        f'<span class="{badge}" title="Rated {escape_html(rating_text)} / 5" '
        f'aria-label="Rated {escape_html(rating_text)} out of 5">'
        f'<span class="bw-rating-star" aria-hidden="true">★</span>'
        f'<span class="bw-rating-value">{escape_html(rating_text)}</span>'
        f"</span>"
    )


def _cuisine_chips_html(cuisine: str | None) -> str:
    if not cuisine:
        return '<span class="bw-chip">All cuisines</span>'
    parts = [p.strip() for p in str(cuisine).replace("|", ",").split(",") if p.strip()]
    if not parts:
        return '<span class="bw-chip">All cuisines</span>'
    return "".join(f'<span class="bw-chip">{escape_html(p)}</span>' for p in parts[:5])


def _cost_label(estimated_cost: str | None) -> str:
    if not estimated_cost:
        return "n/a"
    text = str(estimated_cost).strip()
    # Prefer a short ₹ amount when present; fall back to full string.
    if "₹" in text:
        token = text.split("for")[0].strip()
        return token or text
    return text


def recommendation_card_html(
    *,
    rank: int,
    name: str,
    cuisine: str | None,
    rating: float | None,
    estimated_cost: str | None,
    location: str | None,
    explanation: str | None,
) -> str:
    """Build a Cinematic Epicurean restaurant result card."""
    cuisine_label = escape_html(cuisine or "All cuisines")
    location_label = escape_html(location or "Bangalore")
    cost_short = escape_html(_cost_label(estimated_cost))
    cost_full = escape_html(estimated_cost or "Cost n/a")
    pick_label = f"#{escape_html(rank)} Pick" if int(rank) == 1 else f"#{escape_html(rank)}"
    return f"""
<article class="bw-card">
  <div class="bw-card-banner">
    <div class="bw-card-banner-row">
      <span class="bw-pick">{escape_html(pick_label)}</span>
      {rating_badge_html(rating)}
    </div>
    <p class="bw-card-geo">
      <span>{location_label}</span>
      <span class="bw-dot">·</span>
      <span>{cost_full}</span>
    </p>
  </div>
  <div class="bw-card-body">
    <div class="bw-card-top">
      <div class="bw-card-title-row">
        <span class="bw-rank">#{escape_html(rank)}</span>
        <h3 class="bw-name">{escape_html(name)}</h3>
      </div>
      <div class="bw-cost-block">
        <span class="bw-cost-label">Est. Cost</span>
        <span class="bw-cost-value">{cost_short}</span>
      </div>
    </div>
    <p class="bw-submeta">
      <span>{cuisine_label}</span>
      <span class="bw-dot">·</span>
      <span>{location_label}</span>
    </p>
    <div class="bw-chip-row">{_cuisine_chips_html(cuisine)}</div>
    <div class="bw-insight">
      <span class="bw-insight-icon" aria-hidden="true">✦</span>
      <p class="bw-explain">{escape_html(clamp_explanation(explanation))}</p>
    </div>
  </div>
</article>
""".strip()


def idle_panel_html() -> str:
    """Empty / pre-search tasting-menu panel (Stitch home discover)."""
    return """
<section class="bw-idle" aria-live="polite">
  <div class="bw-idle-icon" aria-hidden="true">🍽</div>
  <h3 class="bw-idle-title">Your AI Tasting Menu Awaits</h3>
  <p class="bw-idle-copy">
    Select your dining mood, location, and cuisine preferences on the left.
    BiteWise will filter verified Bangalore listings and rank an explained shortlist tailored to you.
  </p>
  <div class="bw-idle-presets" aria-hidden="true">
    <span class="bw-preset">Quiet cafes in Indiranagar</span>
    <span class="bw-preset">Best sushi under ₹1500</span>
    <span class="bw-preset">Romantic Cunningham Road</span>
  </div>
  <p class="bw-idle-trust">
    <span class="bw-idle-trust-mark" aria-hidden="true">✓</span>
    Strict ground truth — ratings and cost come from Zomato listings
  </p>
</section>
""".strip()


def empty_state_html(reason: str) -> str:
    """No-match recovery panel (Stitch empty recovery)."""
    return f"""
<section class="bw-empty" role="status">
  <div class="bw-empty-badge">Constraint boundary</div>
  <h3 class="bw-empty-title">No exact matches in this pocket</h3>
  <p class="bw-empty-copy">{escape_html(reason)}</p>
  <p class="bw-empty-hint">
    Try another <strong>location</strong>, lower <strong>minimum rating</strong>,
    add a <strong>cuisine</strong>, or pick a wider <strong>budget</strong>.
  </p>
</section>
""".strip()


def loading_skeleton_html() -> str:
    """AI ranking loading skeleton (Stitch loading state)."""
    return """
<section class="bw-loading" aria-busy="true" aria-live="polite">
  <div class="bw-loading-head">
    <div>
      <p class="bw-loading-kicker">BiteWise Neural Ranker</p>
      <p class="bw-loading-copy">Analyzing Bangalore restaurant candidates…</p>
    </div>
    <span class="bw-loading-pct">Synthesizing</span>
  </div>
  <div class="bw-loading-steps">
    <div class="bw-step bw-step-done"><span>✓</span> Filter pool</div>
    <div class="bw-step bw-step-done"><span>✓</span> Vector alignment</div>
    <div class="bw-step bw-step-active"><span class="bw-pulse"></span> Review synthesis</div>
  </div>
  <div class="bw-skel-card"><div class="bw-skel-banner"></div><div class="bw-skel-line w60"></div><div class="bw-skel-line w90"></div><div class="bw-skel-line w75"></div></div>
  <div class="bw-skel-card"><div class="bw-skel-banner"></div><div class="bw-skel-line w50"></div><div class="bw-skel-line w85"></div><div class="bw-skel-line w70"></div></div>
  <div class="bw-skel-card dim"><div class="bw-skel-banner"></div><div class="bw-skel-line w55"></div><div class="bw-skel-line w80"></div></div>
</section>
""".strip()


def summary_banner_html(summary: str) -> str:
    return (
        f'<div class="bw-summary">'
        f'<span class="bw-summary-kicker">AI executive synthesis</span>'
        f'<p>{escape_html(summary)}</p>'
        f"</div>"
    )


def meta_pills_html(chips: list[str]) -> str:
    return "".join(f'<span class="bw-pill">{escape_html(c)}</span>' for c in chips)

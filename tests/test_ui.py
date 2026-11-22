"""Unit tests for Phase 5 UI rendering helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.ui.options import _extract_options, default_location_index
from src.ui.render import (
    clamp_explanation,
    format_rating,
    rating_badge_class,
    recommendation_card_html,
)


def test_clamp_explanation_empty_and_long():
    assert clamp_explanation(None) == "Recommended based on your filters."
    assert clamp_explanation("") == "Recommended based on your filters."
    long = "word " * 200
    clamped = clamp_explanation(long, limit=40)
    assert len(clamped) <= 40
    assert clamped.endswith("…")


def test_format_rating():
    assert format_rating(4.5) == "4.5"
    assert format_rating(None) == "—"


def test_rating_badge_class_bands():
    assert "bw-rating-high" in rating_badge_class(4.2)
    assert "bw-rating-mid" in rating_badge_class(3.1)
    assert "bw-rating-low" in rating_badge_class(2.0)
    assert "bw-rating-na" in rating_badge_class(None)


def test_default_location_prefers_indiranagar():
    locs = ["Bangalore", "BTM", "Indiranagar", "HSR"]
    assert locs[default_location_index(locs)] == "Indiranagar"


def test_extract_options_reads_numpy_cuisine_tokens():
    frame = pd.DataFrame(
        {
            "location": ["Indiranagar", "HSR"],
            "cuisine_tokens": [
                np.array(["Italian", "Continental"], dtype=object),
                np.array(["Chinese"], dtype=object),
            ],
        }
    )
    locations, cuisines = _extract_options(frame)
    assert locations[0] == "Bangalore"
    assert "Indiranagar" in locations
    assert set(cuisines) == {"Chinese", "Continental", "Italian"}


def test_recommendation_card_html_escapes_and_includes_fields():
    html = recommendation_card_html(
        rank=1,
        name='Tea <Brew>',
        cuisine="Italian",
        rating=4.1,
        estimated_cost="₹500 for two",
        location="Indiranagar",
        explanation="Great fit & cozy.",
    )
    assert "Tea &lt;Brew&gt;" in html
    assert "Italian" in html
    assert "4.1" in html
    assert "bw-rating-high" in html
    assert "bw-rating-star" in html
    assert "★" in html
    assert "₹500 for two" in html
    assert "Indiranagar" in html
    assert "Great fit &amp; cozy." in html
    assert "bw-insight" in html
    assert "#1 Pick" in html
    assert "Est. Cost" in html
    assert "bw-chip" in html

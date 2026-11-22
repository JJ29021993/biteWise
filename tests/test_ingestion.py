"""Unit tests for Phase 1 ingestion helpers (no live HF download required)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.config import Settings
from src.ingestion.columns import PROCESSED_COLUMNS
from src.ingestion.load_dataset import DatasetSchemaError, validate_raw_schema
from src.ingestion.preprocess import (
    assign_budget,
    compute_budget_thresholds,
    load_processed_dataframe,
    parse_cost,
    parse_rating,
    preprocess_dataframe,
    save_processed,
    tokenize_cuisines,
)


def test_validate_raw_schema_missing_columns():
    with pytest.raises(DatasetSchemaError) as exc:
        validate_raw_schema(["name", "location"])
    assert "approx_cost(for two people)" in str(exc.value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("4.1/5", 4.1),
        ("3.8/5", 3.8),
        ("NEW", None),
        ("-", None),
        ("", None),
        (None, None),
        (4.5, 4.5),
        ("6.0/5", None),
    ],
)
def test_parse_rating(value, expected):
    assert parse_rating(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("800", 800.0),
        ("1,200", 1200.0),
        ("₹1,200", 1200.0),
        ("", None),
        (None, None),
        (450, 450.0),
        ("abc", None),
    ],
)
def test_parse_cost(value, expected):
    assert parse_cost(value) == expected


def test_tokenize_cuisines_dedupes_and_splits():
    assert tokenize_cuisines("Italian, Chinese, Italian") == ["Italian", "Chinese"]
    assert tokenize_cuisines(None) == []


def test_budget_thresholds_and_assignment():
    costs = pd.Series([100, 200, 300, 400, 500, 600])
    thresholds = compute_budget_thresholds(costs, low_percentile=33, high_percentile=66)
    assert thresholds["low_max"] <= thresholds["medium_max"]
    assert assign_budget(thresholds["low_max"], thresholds) == "low"
    assert assign_budget(thresholds["medium_max"], thresholds) == "medium"
    assert assign_budget(thresholds["medium_max"] + 1, thresholds) == "high"
    assert assign_budget(None, thresholds) is None


def _sample_raw() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": "Jalsa",
                "location": "banashankari",
                "cuisines": "North Indian, Chinese",
                "rate": "4.1/5",
                "approx_cost(for two people)": "800",
                "votes": 100,
                "listed_in(city)": "Banashankari",
                "listed_in(type)": "Buffet",
                "rest_type": "Casual Dining",
                "online_order": "Yes",
                "book_table": "Yes",
                "dish_liked": "Pasta",
                "address": "Banashankari, Bangalore",
                "url": "https://example.com/jalsa",
            },
            {
                "name": "Jalsa",  # duplicate name+location → keep higher votes
                "location": "Banashankari",
                "cuisines": "North Indian",
                "rate": "3.9/5",
                "approx_cost(for two people)": "700",
                "votes": 10,
                "listed_in(city)": "Banashankari",
                "listed_in(type)": "Buffet",
                "rest_type": "Casual Dining",
                "online_order": "Yes",
                "book_table": "No",
                "dish_liked": None,
                "address": "Banashankari, Bangalore",
                "url": "https://example.com/jalsa-dup",
            },
            {
                "name": None,  # dropped
                "location": "Indiranagar",
                "cuisines": "Italian",
                "rate": "NEW",
                "approx_cost(for two people)": "1,200",
                "votes": 5,
            },
            {
                "name": "Cheap Bites",
                "location": "Indiranagar",
                "cuisines": "Street Food",
                "rate": "-",
                "approx_cost(for two people)": "200",
                "votes": 20,
                "listed_in(city)": "Indiranagar",
                "listed_in(type)": "Delivery",
                "rest_type": "Quick Bites",
                "online_order": "Yes",
                "book_table": "No",
                "dish_liked": None,
                "address": "Indiranagar, Bangalore",
                "url": "https://example.com/cheap",
            },
            {
                "name": "Luxury Table",
                "location": "Indiranagar",
                "cuisines": "Italian, Continental",
                "rate": "4.8/5",
                "approx_cost(for two people)": "₹2,500",
                "votes": 50,
                "listed_in(city)": "Indiranagar",
                "listed_in(type)": "Dine-out",
                "rest_type": "Fine Dining",
                "online_order": "No",
                "book_table": "Yes",
                "dish_liked": "Pasta",
                "address": "Indiranagar, Bangalore",
                "url": "https://example.com/luxury",
            },
        ]
    )


def test_preprocess_dataframe_cleans_and_dedupes():
    processed, meta = preprocess_dataframe(_sample_raw())
    assert list(processed.columns) == list(PROCESSED_COLUMNS)
    assert len(processed) == 3  # nameless dropped, duplicate collapsed
    assert processed["name"].notna().all()
    jalsa = processed[processed["name"] == "Jalsa"].iloc[0]
    assert jalsa["votes"] == 100
    assert jalsa["location"] == "Banashankari"
    # title-case should not mangle ordinals like 5th
    raw_ord = _sample_raw()
    raw_ord.loc[0, "location"] = "koramangala 5th block"
    loc_check, _ = preprocess_dataframe(raw_ord)
    assert "Koramangala 5th Block" in set(loc_check["location"])
    assert "Chinese" in jalsa["cuisine_tokens"]
    assert processed["city"].eq("Bangalore").all()
    assert "budget_thresholds" in meta
    assert meta["row_count"] == 3


def test_save_and_load_processed_roundtrip(tmp_path: Path):
    settings = Settings(
        data_raw_dir=tmp_path / "raw",
        data_processed_dir=tmp_path / "processed",
    )
    processed, meta = preprocess_dataframe(_sample_raw())
    save_processed(processed, meta, settings)

    loaded = load_processed_dataframe(settings)
    assert len(loaded) == len(processed)
    assert loaded["name"].tolist() == processed["name"].tolist()
    assert (tmp_path / "processed" / "budget_thresholds.json").exists()


def test_load_processed_missing_file(tmp_path: Path):
    settings = Settings(data_processed_dir=tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        load_processed_dataframe(settings)


def test_budget_labels_reproducible_from_cost():
    """Exit criterion: budget labels must recompute from cost + thresholds."""
    processed, meta = preprocess_dataframe(_sample_raw())
    thresholds = meta["budget_thresholds"]
    assert "low_max" in thresholds and "medium_max" in thresholds
    for _, row in processed.iterrows():
        cost = row["cost_for_two"]
        if cost is None or (isinstance(cost, float) and pd.isna(cost)):
            assert row["budget"] is None or pd.isna(row["budget"])
        else:
            assert assign_budget(float(cost), thresholds) == row["budget"]


def test_processed_key_columns_non_null_for_working_set():
    processed, _ = preprocess_dataframe(_sample_raw())
    assert processed["name"].notna().all()
    assert processed["location"].notna().all()
    assert processed["restaurant_id"].notna().all()
    # Rating/cost may be null for some rows, but cuisine string should exist
    # after name/location filtering (street-food row may lack rating).
    assert processed["cuisines"].notna().all()


def test_budget_thresholds_stable_across_identical_inputs():
    costs = pd.Series([100, 200, 300, 400, 500, 600, 700, 800])
    a = compute_budget_thresholds(costs, low_percentile=33, high_percentile=66)
    b = compute_budget_thresholds(costs, low_percentile=33, high_percentile=66)
    assert a == b

import pytest
from pathlib import Path
from part2_engine.growth_engine import (
    mom_growth,
    is_flagged,
    classify_growth,
    validate_feed
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

def test_mom_growth_normal_positive():
    assert mom_growth(100.0, 120.0) == 20.0

def test_mom_growth_normal_negative():
    assert mom_growth(100.0, 80.0) == -20.0

def test_mom_growth_zero_baseline():
    assert mom_growth(0.0, 0.0) == 0.0
    assert mom_growth(0.0, 150.0) == "new_revenue"

def test_flagging_below_threshold():
    assert is_flagged(5.0) is False
    assert is_flagged(-5.0) is False
    assert classify_growth(5.0) == "normal"
    assert classify_growth(-5.0) == "normal"

def test_flagging_above_threshold():
    assert is_flagged(10.0) is True
    assert is_flagged(-10.0) is True
    assert classify_growth(10.0) == "flagged"
    assert classify_growth(-10.0) == "flagged"

def test_exact_boundary_escalation():
    # Exact +8% and -8% should classify as 'escalated' and NOT ordinary flagged
    assert is_flagged(8.0) is False
    assert is_flagged(-8.0) is False
    assert classify_growth(8.0) == "escalated"
    assert classify_growth(-8.0) == "escalated"

def test_validate_feed_valid(tmp_path):
    valid_csv = tmp_path / "valid.csv"
    valid_csv.write_text(
        "month,category,revenue,n_orders\n"
        "April,Ethnic Wear,100000.0,50\n"
        "April,Western Wear,80000.0,40\n"
        "April,Kids Wear,60000.0,30\n"
        "April,Beauty & Personal Care,40000.0,20\n"
        "April,Home & Kitchen,50000.0,25\n"
    )
    valid, errors = validate_feed(valid_csv)
    assert valid is True
    assert errors == []

def test_validate_feed_invalid():
    corrupted_path = FIXTURES_DIR / "corrupted_feed.csv"
    valid, errors = validate_feed(corrupted_path)
    assert valid is False
    assert len(errors) > 0

def test_validate_feed_nonexistent():
    valid, errors = validate_feed("non_existent_file.csv")
    assert valid is False
    assert "File not found" in errors[0]

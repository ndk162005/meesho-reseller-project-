import pytest
import csv
from pathlib import Path
from part4_agent.mock_agent_runner import run

def test_agent_may_scenario(tmp_path):
    prev_csv = tmp_path / "april.csv"
    curr_csv = tmp_path / "may.csv"

    prev_csv.write_text(
        "month,category,revenue,n_orders\n"
        "April,Ethnic Wear,104520.77,64\n"
        "April,Western Wear,95400.50,62\n"
        "April,Kids Wear,78200.30,58\n"
        "April,Beauty & Personal Care,52100.20,56\n"
        "April,Home & Kitchen,68500.40,60\n"
    )

    curr_csv.write_text(
        "month,category,revenue,n_orders\n"
        "May,Ethnic Wear,185107.61,95\n"       # +77.10%
        "May,Western Wear,72886.00,50\n"       # -23.60%
        "May,Kids Wear,59839.00,46\n"          # -23.48%
        "May,Beauty & Personal Care,35544.00,52\n" # -31.79% -> flagged
        "May,Home & Kitchen,62100.00,57\n"     # -9.34% -> flagged
    )

    res = run("May", str(prev_csv), str(curr_csv))

    assert res["validation_status"] == "valid"
    assert res["action_taken"] == "drafted_and_held_for_approval"
    assert len(res["flagged_categories"]) == 5
    assert len(res["drafted_categories"]) == 3
    assert len(res["suppressed_categories"]) == 2

    # Top drafted category must be Ethnic Wear (+77.10%)
    top_drafted = res["drafted_categories"][0]
    assert top_drafted["category"] == "Ethnic Wear"
    assert top_drafted["mom_pct"] == 77.10

def test_agent_invalid_feed_scenario(tmp_path):
    curr_csv = tmp_path / "corrupted.csv"
    prev_csv = tmp_path / "april.csv"

    curr_csv.write_text(
        "month,category,revenue,n_orders\n"
        "May,Ethnic Wear,-500.0,10\n"
    )
    prev_csv.write_text("month,category,revenue,n_orders\n")

    res = run("May", str(prev_csv), str(curr_csv))

    assert res["validation_status"] == "invalid"
    assert res["action_taken"] == "hard_stop"
    assert len(res["flagged_categories"]) == 0
    assert len(res["drafted_categories"]) == 0

def test_agent_exact_boundary_escalation(tmp_path):
    prev_csv = tmp_path / "april.csv"
    curr_csv = tmp_path / "may.csv"

    prev_csv.write_text(
        "month,category,revenue,n_orders\n"
        "April,Ethnic Wear,100.0,10\n"
        "April,Western Wear,100.0,10\n"
        "April,Kids Wear,100.0,10\n"
        "April,Beauty & Personal Care,100.0,10\n"
        "April,Home & Kitchen,100.0,10\n"
    )

    curr_csv.write_text(
        "month,category,revenue,n_orders\n"
        "May,Ethnic Wear,108.0,10\n"          # +8.0% -> escalated
        "May,Western Wear,92.0,10\n"          # -8.0% -> escalated
        "May,Kids Wear,150.0,10\n"           # +50.0% -> flagged
        "May,Beauty & Personal Care,102.0,10\n" # +2.0% -> normal
        "May,Home & Kitchen,100.0,10\n"       # 0.0% -> normal
    )

    res = run("May", str(prev_csv), str(curr_csv))

    assert res["validation_status"] == "valid"
    assert len(res["escalated_categories"]) == 2
    escalated_cats = [c["category"] for c in res["escalated_categories"]]
    assert "Ethnic Wear" in escalated_cats
    assert "Western Wear" in escalated_cats

    # Verify escalated categories are not placed into suppressed
    suppressed_cats = [c["category"] for c in res["suppressed_categories"]]
    assert "Ethnic Wear" not in suppressed_cats
    assert "Western Wear" not in suppressed_cats

def test_agent_uses_part2_engine():
    import part4_agent.mock_agent_runner as runner
    assert hasattr(runner, "mom_growth")
    assert hasattr(runner, "classify_growth")
    assert hasattr(runner, "validate_feed")

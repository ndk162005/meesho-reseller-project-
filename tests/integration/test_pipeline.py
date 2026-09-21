import pytest
import sqlite3
import csv
from pathlib import Path

from data.generate_dataset import generate_data
from part1_sql.run_queries import run_sql_analytics
from part2_engine.growth_engine import validate_feed, mom_growth, classify_growth
from part3_narrative.narrative_generator import generate_narrative
from part3_narrative.narrative_validator import validate_narrative
from part4_agent.mock_agent_runner import run as run_agent

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_DIR / "data" / "meesho_reseller.db"
OUTPUT_DIR = PROJECT_DIR / "part1_sql" / "output"
MONTHLY_CSV = OUTPUT_DIR / "monthly_category_revenue.csv"

def test_full_pipeline_integration(tmp_path):
    # 1. Generate Dataset
    generate_data()
    assert DB_PATH.exists()

    # 2. Verify Database Counts
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM resellers;")
    n_resellers = cursor.fetchone()[0]
    assert n_resellers == 24

    cursor.execute("SELECT COUNT(*) FROM orders;")
    n_orders = cursor.fetchone()[0]
    assert n_orders == 900

    # RS024 zero orders check
    cursor.execute("SELECT COUNT(*) FROM orders WHERE reseller_id = 'RS024';")
    rs024_orders = cursor.fetchone()[0]
    assert rs024_orders == 0

    conn.close()

    # 3. Run SQL Analytics
    run_sql_analytics()
    assert MONTHLY_CSV.exists()

    # 4. Validate Feed
    valid, errors = validate_feed(MONTHLY_CSV)
    assert valid is True
    assert errors == []

    # 5. Check Acceptance Values in SQL CSV Output
    with open(MONTHLY_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # April Ethnic Wear
    apr_ethnic = [r for r in rows if r["month"] == "April" and r["category"] == "Ethnic Wear"][0]
    assert float(apr_ethnic["revenue"]) == 104520.77
    assert int(apr_ethnic["n_orders"]) == 64

    # June Beauty & Personal Care
    june_beauty = [r for r in rows if r["month"] == "June" and r["category"] == "Beauty & Personal Care"][0]
    assert float(june_beauty["revenue"]) == 37559.07
    assert int(june_beauty["n_orders"]) == 52

    # June AOV check
    june_aov_csv = OUTPUT_DIR / "june_aov.csv"
    with open(june_aov_csv, "r", encoding="utf-8") as f:
        aov_row = list(csv.DictReader(f))[0]
    assert float(aov_row["aov"]) == 1267.69

    # 6. Test Growth Engine Calculation & Narrative Generation
    may_ethnic = [r for r in rows if r["month"] == "May" and r["category"] == "Ethnic Wear"][0]
    mom_ethnic = mom_growth(apr_ethnic["revenue"], may_ethnic["revenue"])
    assert mom_ethnic == 77.10

    narrative = generate_narrative({
        "category": "Ethnic Wear",
        "previous_month": "April",
        "current_month": "May",
        "previous_revenue": float(apr_ethnic["revenue"]),
        "current_revenue": float(may_ethnic["revenue"]),
        "mom_pct": mom_ethnic
    })
    v_valid, v_errors = validate_narrative(narrative, "Ethnic Wear", "+77.10%")
    assert v_valid is True

    # 7. Run Agent Orchestration with Separate April & May Feeds
    apr_csv = tmp_path / "april_feed.csv"
    may_csv = tmp_path / "may_feed.csv"

    apr_rows = [r for r in rows if r["month"] == "April"]
    may_rows = [r for r in rows if r["month"] == "May"]

    with open(apr_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["month", "category", "revenue", "n_orders"])
        writer.writeheader()
        writer.writerows(apr_rows)

    with open(may_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["month", "category", "revenue", "n_orders"])
        writer.writeheader()
        writer.writerows(may_rows)

    agent_result = run_agent("May", str(apr_csv), str(may_csv))
    assert agent_result["validation_status"] == "valid"
    assert agent_result["action_taken"] == "drafted_and_held_for_approval"
    assert len(agent_result["drafted_categories"]) == 3

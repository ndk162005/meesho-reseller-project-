import argparse
import csv
import json
import sys
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from data.generate_dataset import generate_data
from part1_sql.run_queries import run_sql_analytics
from part2_engine.growth_engine import validate_feed, mom_growth, classify_growth
from part3_narrative.narrative_generator import generate_narrative
from part3_narrative.narrative_validator import validate_narrative
from part4_agent.mock_agent_runner import run as run_agent

PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "data" / "meesho_reseller.db"
MONTHLY_CSV = PROJECT_DIR / "part1_sql" / "output" / "monthly_category_revenue.csv"

def _extract_monthly_csv(month_name: str, target_csv: Path):
    if not MONTHLY_CSV.exists():
        return
    with open(MONTHLY_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    month_rows = [r for r in rows if r["month"] == month_name]
    with open(target_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["month", "category", "revenue", "n_orders"])
        writer.writeheader()
        writer.writerows(month_rows)

def run_pipeline(regenerate: bool = False):
    print("==================================================")
    print("  MEESHO RESELLER INTELLIGENCE PIPELINE RUNNER   ")
    print("==================================================")

    # Step 1: Dataset Generation
    if regenerate or not DB_PATH.exists():
        print("\n[Step 1] Generating deterministic dataset & SQLite database...")
        generate_data()
    else:
        print("\n[Step 1] Using existing dataset & SQLite database (use --regenerate to rebuild).")

    # Step 2: SQL Analytics
    print("\n[Step 2] Executing SQL Analytics...")
    run_sql_analytics()

    # Step 3: Feed Validation
    print("\n[Step 3] Validating Monthly Category Revenue Feed...")
    is_valid, errors = validate_feed(MONTHLY_CSV)
    if not is_valid:
        print(f"FAILED: Feed validation errors: {errors}")
        sys.exit(1)
    print("SUCCESS: Feed validation passed.")

    # Step 4: Narrative System Verification
    print("\n[Step 4] Generating Sample Business Narratives...")
    sample_narrative = generate_narrative({
        "category": "Ethnic Wear",
        "previous_month": "April",
        "current_month": "May",
        "previous_revenue": 104520.77,
        "current_revenue": 185107.61,
        "mom_pct": 77.10
    })
    print("\n--- May Ethnic Wear Sample Narrative ---")
    print(sample_narrative)

    v_valid, v_errors = validate_narrative(sample_narrative, "Ethnic Wear", "+77.10%")
    print(f"Narrative Validation: {'PASSED' if v_valid else 'FAILED'}")

    # Step 5: Mock Agent Orchestration (May & June Scenarios)
    print("\n[Step 5] Running Mock AI Agent Orchestration...")
    
    tmp_dir = PROJECT_DIR / "part1_sql" / "output"
    apr_csv = tmp_dir / "april_category_revenue.csv"
    may_csv = tmp_dir / "may_category_revenue.csv"
    june_csv = tmp_dir / "june_category_revenue.csv"

    _extract_monthly_csv("April", apr_csv)
    _extract_monthly_csv("May", may_csv)
    _extract_monthly_csv("June", june_csv)

    print("\n--- May Scenario Agent Output (Comparing May vs April) ---")
    may_agent_output = run_agent("May", str(apr_csv), str(may_csv))
    print(json.dumps(may_agent_output, indent=2))

    print("\n--- June Scenario Agent Output (Comparing June vs May) ---")
    june_agent_output = run_agent("June", str(may_csv), str(june_csv))
    print(json.dumps(june_agent_output, indent=2))

    print("\n==================================================")
    print("     PIPELINE EXECUTED SUCCESSFULLY END-TO-END    ")
    print("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meesho Reseller Intelligence Pipeline")
    parser.add_argument("--regenerate", action="store_true", help="Force dataset regeneration")
    args = parser.parse_args()
    run_pipeline(regenerate=args.regenerate)

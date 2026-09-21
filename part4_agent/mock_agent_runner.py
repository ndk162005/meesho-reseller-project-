import csv
import json
from pathlib import Path
from typing import Dict, Any, List

from part2_engine.growth_engine import (
    validate_feed,
    mom_growth,
    is_flagged,
    classify_growth
)
from part4_agent.agent_models import AgentResult, CategoryGrowth

def _load_category_revenue(csv_path: Path) -> Dict[str, float]:
    data = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row["category"].strip()
            rev = float(row["revenue"].strip())
            data[cat] = rev
    return data

def run(month: str, previous_month_csv: str, current_month_csv: str) -> Dict[str, Any]:
    curr_path = Path(current_month_csv)
    prev_path = Path(previous_month_csv)

    # 1. Validate Current Feed
    is_valid, errors = validate_feed(curr_path)
    if not is_valid:
        result = AgentResult(
            run_month=month,
            validation_status="invalid",
            validation_errors=errors,
            action_taken="hard_stop"
        )
        return result.to_dict()

    # Also validate previous feed exists
    if not prev_path.exists():
        result = AgentResult(
            run_month=month,
            validation_status="invalid",
            validation_errors=[f"Previous feed file not found: {prev_path}"],
            action_taken="hard_stop"
        )
        return result.to_dict()

    # 2. Load Revenue Data
    curr_data = _load_category_revenue(curr_path)
    prev_data = _load_category_revenue(prev_path)

    flagged_list: List[Dict[str, Any]] = []
    escalated_list: List[Dict[str, Any]] = []
    normal_list: List[Dict[str, Any]] = []

    # 3. Compute Growth & Classify using Part 2 Functions
    for category, curr_rev in curr_data.items():
        prev_rev = prev_data.get(category, 0.0)
        mom_val = mom_growth(prev_rev, curr_rev)
        classification = classify_growth(mom_val)

        growth_record = CategoryGrowth(
            category=category,
            previous_revenue=prev_rev,
            current_revenue=curr_rev,
            mom_pct=mom_val,
            classification=classification
        )
        rec_dict = growth_record.__dict__

        if classification == "escalated":
            escalated_list.append(rec_dict)
        elif classification == "flagged":
            flagged_list.append(rec_dict)
        else:
            normal_list.append(rec_dict)

    # 4. Sort Flagged Categories by abs(mom_pct) Descending
    def sort_key(item: Dict[str, Any]) -> float:
        val = item["mom_pct"]
        if val == "new_revenue":
            return 999999.0
        return abs(float(val))

    flagged_list.sort(key=sort_key, reverse=True)

    # 5. Top 3 Drafted, Remaining Suppressed
    drafted_list = flagged_list[:3]
    suppressed_list = flagged_list[3:]

    # 6. Construct Agent Structured Result
    result = AgentResult(
        run_month=month,
        validation_status="valid",
        validation_errors=[],
        flagged_categories=flagged_list,
        drafted_categories=drafted_list,
        suppressed_categories=suppressed_list,
        escalated_categories=escalated_list,
        action_taken="drafted_and_held_for_approval"
    )

    return result.to_dict()

if __name__ == "__main__":
    # Example execution for demonstration
    res = run("May", "part1_sql/output/monthly_category_revenue.csv", "part1_sql/output/monthly_category_revenue.csv")
    print(json.dumps(res, indent=2))

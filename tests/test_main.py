import json
import pytest
from pathlib import Path
from main import (
    pipeline_state,
    run_pipeline_step,
    get_all_process_data,
    read_csv_as_dicts,
)

def test_pipeline_step_execution():
    """Verify individual steps can execute and report completed status."""
    # Step 1
    assert run_pipeline_step("step1_data", force_regenerate=False) is True
    assert pipeline_state.step_statuses["step1_data"]["status"] == "completed"

    # Step 2
    assert run_pipeline_step("step2_sql") is True
    assert pipeline_state.step_statuses["step2_sql"]["status"] == "completed"

    # Step 3
    assert run_pipeline_step("step3_growth") is True
    assert pipeline_state.step_statuses["step3_growth"]["status"] == "completed"

    # Step 4
    assert run_pipeline_step("step4_narrative") is True
    assert pipeline_state.step_statuses["step4_narrative"]["status"] == "completed"

    # Step 5
    assert run_pipeline_step("step5_agent") is True
    assert pipeline_state.step_statuses["step5_agent"]["status"] == "completed"

def test_get_all_process_data_structure():
    """Verify get_all_process_data returns full structure for all 5 processes."""
    data = get_all_process_data()
    
    assert "process1_dataset" in data
    assert "process2_sql" in data
    assert "process3_growth" in data
    assert "process4_narrative" in data
    assert "process5_agent" in data

    # Process 1 checks
    p1 = data["process1_dataset"]
    assert p1["total_resellers"] == 24
    assert p1["total_orders"] == 900
    assert p1["db_exists"] is True

    # Process 2 checks
    p2 = data["process2_sql"]
    assert len(p2["monthly_category_revenue"]) > 0
    assert len(p2["region_revenue"]) == 4
    assert len(p2["top_resellers"]) == 5
    assert len(p2["zero_order_resellers"]) == 1
    assert p2["zero_order_resellers"][0]["reseller_id"] == "RS024"

    # Process 3 checks
    p3 = data["process3_growth"]
    assert p3["feed_validation"]["is_valid"] is True
    assert len(p3["may_growth"]) == 5
    assert len(p3["june_growth"]) == 5

    # Process 4 checks
    p4 = data["process4_narrative"]
    assert len(p4["narratives"]) == 5
    for narr in p4["narratives"]:
        assert narr["is_valid"] is True

    # Process 5 checks
    p5 = data["process5_agent"]
    assert p5["may_scenario"]["validation_status"] == "valid"
    assert len(p5["may_scenario"]["drafted_categories"]) <= 3

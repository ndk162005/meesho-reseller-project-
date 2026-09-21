import argparse
import csv
import io
import json
import os
import sqlite3
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

# Ensure UTF-8 output encoding on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
DB_PATH = PROJECT_DIR / "data" / "meesho_reseller.db"
RESELLERS_CSV = PROJECT_DIR / "data" / "resellers.csv"
ORDERS_CSV = PROJECT_DIR / "data" / "orders.csv"
SQL_OUTPUT_DIR = PROJECT_DIR / "part1_sql" / "output"
MONTHLY_CSV = SQL_OUTPUT_DIR / "monthly_category_revenue.csv"

# Import existing modular components
from data.generate_dataset import generate_data
from part1_sql.run_queries import run_sql_analytics
from part2_engine.growth_engine import (
    classify_growth,
    is_flagged,
    mom_growth,
    validate_feed,
)
from part3_narrative.masking import mask_reseller_name
from part3_narrative.narrative_generator import generate_narrative
from part3_narrative.narrative_validator import validate_narrative
from part4_agent.mock_agent_runner import run as run_agent


class PipelineStateManager:
    """Thread-safe state manager for pipeline executions and log buffering."""

    def __init__(self):
        self._lock = threading.Lock()
        self.is_running = False
        self.current_step = None
        self.last_run_timestamp: Optional[str] = None
        self.logs: List[Dict[str, Any]] = []
        self.step_statuses: Dict[str, Dict[str, Any]] = {
            "step1_data": {"name": "Dataset & SQLite", "status": "idle", "duration": None},
            "step2_sql": {"name": "SQL Analytics Engine", "status": "idle", "duration": None},
            "step3_growth": {"name": "MoM Growth & Feed Validation", "status": "idle", "duration": None},
            "step4_narrative": {"name": "PII Masking & Business Narratives", "status": "idle", "duration": None},
            "step5_agent": {"name": "Autonomous AI Agent Orchestration", "status": "idle", "duration": None},
        }

    def log(self, message: str, level: str = "info", step: Optional[str] = None):
        timestamp = time.strftime("%H:%M:%S")
        with self._lock:
            log_entry = {
                "id": len(self.logs) + 1,
                "time": timestamp,
                "level": level,
                "step": step or self.current_step,
                "message": message,
            }
            self.logs.append(log_entry)
            # Keep at most 2000 log entries
            if len(self.logs) > 2000:
                self.logs = self.logs[-2000:]
        print(f"[{timestamp}] [{level.upper()}] {message}")

    def update_step(self, step_key: str, status: str, duration: Optional[float] = None, error: Optional[str] = None):
        with self._lock:
            if step_key in self.step_statuses:
                self.step_statuses[step_key]["status"] = status
                if duration is not None:
                    self.step_statuses[step_key]["duration"] = round(duration, 3)
                if error:
                    self.step_statuses[step_key]["error"] = error

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            db_exists = DB_PATH.exists()
            return {
                "is_running": self.is_running,
                "current_step": self.current_step,
                "last_run_timestamp": self.last_run_timestamp,
                "step_statuses": self.step_statuses,
                "total_logs": len(self.logs),
                "db_initialized": db_exists,
            }

    def get_logs_since(self, last_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            return [log for log in self.logs if log["id"] > last_id]

    def clear_logs(self):
        with self._lock:
            self.logs = []


pipeline_state = PipelineStateManager()


def _extract_monthly_csv(month_name: str, target_csv: Path):
    if not MONTHLY_CSV.exists():
        return
    with open(MONTHLY_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    month_rows = [r for r in rows if r["month"] == month_name]
    target_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(target_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["month", "category", "revenue", "n_orders"])
        writer.writeheader()
        writer.writerows(month_rows)


def run_pipeline_step(step_key: str, force_regenerate: bool = False) -> bool:
    """Executes a single step of the pipeline with state updates."""
    start_time = time.time()
    pipeline_state.current_step = step_key
    pipeline_state.update_step(step_key, "running")

    try:
        if step_key == "step1_data":
            pipeline_state.log("Generating deterministic dataset and SQLite database...", level="info", step=step_key)
            if force_regenerate or not DB_PATH.exists():
                generate_data()
                pipeline_state.log("Dataset generated: 24 resellers, 900 orders, SQLite initialized.", level="success", step=step_key)
            else:
                pipeline_state.log("Using existing SQLite database (data/meesho_reseller.db).", level="info", step=step_key)

        elif step_key == "step2_sql":
            pipeline_state.log("Executing SQL analytics queries...", level="info", step=step_key)
            if not DB_PATH.exists():
                pipeline_state.log("Database missing. Generating data first...", level="warning", step=step_key)
                generate_data()
            run_sql_analytics()
            pipeline_state.log("SQL analytics complete. Generated all 5 query outputs in part1_sql/output/.", level="success", step=step_key)

        elif step_key == "step3_growth":
            pipeline_state.log("Validating CSV feed and computing MoM growth rates...", level="info", step=step_key)
            if not MONTHLY_CSV.exists():
                run_sql_analytics()
            is_valid, errors = validate_feed(MONTHLY_CSV)
            if not is_valid:
                err_msg = f"Feed validation failed: {errors}"
                pipeline_state.log(err_msg, level="error", step=step_key)
                pipeline_state.update_step(step_key, "error", duration=time.time() - start_time, error=err_msg)
                return False
            pipeline_state.log("Feed validation passed: All 5 categories present with positive revenues.", level="success", step=step_key)

        elif step_key == "step4_narrative":
            pipeline_state.log("Generating business narratives with PII hash masking...", level="info", step=step_key)
            sample_record = {
                "category": "Ethnic Wear",
                "previous_month": "April",
                "current_month": "May",
                "previous_revenue": 104520.77,
                "current_revenue": 185107.61,
                "mom_pct": 77.10,
                "top_reseller": "Rajesh Kumar",
            }
            narrative = generate_narrative(sample_record)
            v_valid, v_errors = validate_narrative(narrative, "Ethnic Wear", "+77.10%")
            if not v_valid:
                pipeline_state.log(f"Narrative validation failed: {v_errors}", level="error", step=step_key)
                pipeline_state.update_step(step_key, "error", duration=time.time() - start_time, error=str(v_errors))
                return False
            pipeline_state.log(f"Narrative successfully generated and validated for Ethnic Wear (+77.10%). Masked PII: '{sample_record['top_reseller']}' -> '{mask_reseller_name(sample_record['top_reseller'])}'.", level="success", step=step_key)

        elif step_key == "step5_agent":
            pipeline_state.log("Executing Autonomous Mock AI Agent for May and June scenarios...", level="info", step=step_key)
            tmp_dir = SQL_OUTPUT_DIR
            apr_csv = tmp_dir / "april_category_revenue.csv"
            may_csv = tmp_dir / "may_category_revenue.csv"
            june_csv = tmp_dir / "june_category_revenue.csv"

            _extract_monthly_csv("April", apr_csv)
            _extract_monthly_csv("May", may_csv)
            _extract_monthly_csv("June", june_csv)

            may_res = run_agent("May", str(apr_csv), str(may_csv))
            june_res = run_agent("June", str(may_csv), str(june_csv))

            pipeline_state.log(f"May Scenario Agent Result: Status={may_res['validation_status']}, Action={may_res['action_taken']}, Drafted={len(may_res.get('drafted_categories', []))}", level="success", step=step_key)
            pipeline_state.log(f"June Scenario Agent Result: Status={june_res['validation_status']}, Action={june_res['action_taken']}, Drafted={len(june_res.get('drafted_categories', []))}", level="success", step=step_key)

        else:
            raise ValueError(f"Unknown step: {step_key}")

        elapsed = time.time() - start_time
        pipeline_state.update_step(step_key, "completed", duration=elapsed)
        return True

    except Exception as e:
        elapsed = time.time() - start_time
        err_msg = str(e)
        pipeline_state.log(f"Error in {step_key}: {err_msg}", level="error", step=step_key)
        pipeline_state.update_step(step_key, "error", duration=elapsed, error=err_msg)
        return False


def run_full_pipeline_task(regenerate: bool = False):
    """Orchestrates the entire 5-step pipeline sequentially in a background thread."""
    with pipeline_state._lock:
        if pipeline_state.is_running:
            return
        pipeline_state.is_running = True
        pipeline_state.last_run_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    pipeline_state.log("========== STARTING MEESHO RESELLER INTELLIGENCE PIPELINE ==========", level="info")
    steps = ["step1_data", "step2_sql", "step3_growth", "step4_narrative", "step5_agent"]
    success = True

    try:
        for step in steps:
            ok = run_pipeline_step(step, force_regenerate=(regenerate if step == "step1_data" else False))
            if not ok:
                success = False
                pipeline_state.log(f"Pipeline stopped due to error in {step}.", level="error")
                break

        if success:
            pipeline_state.log("========== PIPELINE EXECUTED SUCCESSFULLY END-TO-END ==========", level="success")
    finally:
        with pipeline_state._lock:
            pipeline_state.is_running = False
            pipeline_state.current_step = None


def read_csv_as_dicts(csv_path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not csv_path.exists():
        return []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            rows.append(row)
        return rows


def get_all_process_data() -> Dict[str, Any]:
    """Compiles comprehensive structured data for every pipeline process."""
    data = {}

    # Process 1 Data: Database & Reseller / Order Stats
    resellers = read_csv_as_dicts(RESELLERS_CSV)
    orders_sample = read_csv_as_dicts(ORDERS_CSV, limit=100)
    total_orders_count = 0
    month_counts = {"April": 0, "May": 0, "June": 0}
    status_counts = {"Delivered": 0, "Cancelled": 0, "Returned": 0}

    if ORDERS_CSV.exists():
        with open(ORDERS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                total_orders_count += 1
                m = r.get("order_date", "")[5:7]
                if m == "04":
                    month_counts["April"] += 1
                elif m == "05":
                    month_counts["May"] += 1
                elif m == "06":
                    month_counts["June"] += 1
                st = r.get("order_status", "Unknown")
                status_counts[st] = status_counts.get(st, 0) + 1

    data["process1_dataset"] = {
        "db_exists": DB_PATH.exists(),
        "total_resellers": len(resellers),
        "total_orders": total_orders_count,
        "month_distribution": month_counts,
        "status_distribution": status_counts,
        "resellers": resellers,
        "orders_sample": orders_sample,
    }

    # Process 2 Data: SQL Analytics Query Outputs
    data["process2_sql"] = {
        "monthly_category_revenue": read_csv_as_dicts(SQL_OUTPUT_DIR / "monthly_category_revenue.csv"),
        "region_revenue": read_csv_as_dicts(SQL_OUTPUT_DIR / "region_revenue.csv"),
        "top_resellers": read_csv_as_dicts(SQL_OUTPUT_DIR / "top_resellers.csv"),
        "zero_order_resellers": read_csv_as_dicts(SQL_OUTPUT_DIR / "zero_order_resellers.csv"),
        "zero_order_count_demo": read_csv_as_dicts(SQL_OUTPUT_DIR / "zero_order_count_demo.csv"),
        "june_aov": read_csv_as_dicts(SQL_OUTPUT_DIR / "june_aov.csv"),
    }

    # Process 3 Data: MoM Growth Calculations & Feed Validation
    feed_valid, feed_errors = (True, [])
    if MONTHLY_CSV.exists():
        feed_valid, feed_errors = validate_feed(MONTHLY_CSV)
    else:
        feed_valid = False
        feed_errors = ["Monthly category revenue CSV not found. Run SQL analytics first."]

    # Calculate MoM for April -> May and May -> June
    monthly_rows = data["process2_sql"]["monthly_category_revenue"]
    by_month_cat = {}
    for r in monthly_rows:
        by_month_cat[(r["month"], r["category"])] = float(r["revenue"])

    categories = [
        "Ethnic Wear",
        "Western Wear",
        "Kids Wear",
        "Beauty & Personal Care",
        "Home & Kitchen",
    ]

    growth_may = []
    growth_june = []

    for cat in categories:
        apr_rev = by_month_cat.get(("April", cat), 0.0)
        may_rev = by_month_cat.get(("May", cat), 0.0)
        jun_rev = by_month_cat.get(("June", cat), 0.0)

        # May vs April
        mom_may = mom_growth(apr_rev, may_rev)
        class_may = classify_growth(mom_may)
        growth_may.append({
            "category": cat,
            "prev_revenue": apr_rev,
            "curr_revenue": may_rev,
            "mom_pct": mom_may,
            "classification": class_may,
            "flagged": is_flagged(mom_may),
        })

        # June vs May
        mom_jun = mom_growth(may_rev, jun_rev)
        class_jun = classify_growth(mom_jun)
        growth_june.append({
            "category": cat,
            "prev_revenue": may_rev,
            "curr_revenue": jun_rev,
            "mom_pct": mom_jun,
            "classification": class_jun,
            "flagged": is_flagged(mom_jun),
        })

    data["process3_growth"] = {
        "feed_validation": {"is_valid": feed_valid, "errors": feed_errors},
        "threshold": 8.0,
        "may_growth": growth_may,
        "june_growth": growth_june,
    }

    # Process 4 Data: PII Masking & Narratives
    narratives = []
    top_reseller_name = "Rajesh Kumar"
    for item in growth_may:
        narr_text = generate_narrative({
            "category": item["category"],
            "previous_month": "April",
            "current_month": "May",
            "previous_revenue": item["prev_revenue"],
            "current_revenue": item["curr_revenue"],
            "mom_pct": item["mom_pct"],
            "top_reseller": top_reseller_name,
        })
        expected_mom_str = f"{item['mom_pct']:+.2f}%" if isinstance(item["mom_pct"], (int, float)) else "+100.00%"
        is_valid_narr, narr_errs = validate_narrative(narr_text, item["category"], expected_mom_str)
        narratives.append({
            "category": item["category"],
            "month": "May",
            "mom_pct": item["mom_pct"],
            "narrative": narr_text,
            "is_valid": is_valid_narr,
            "errors": narr_errs,
        })

    sample_maskings = []
    for r in resellers[:8]:
        sample_maskings.append({
            "original_name": r["reseller_name"],
            "reseller_id": r["reseller_id"],
            "region": r["region"],
            "masked_name": mask_reseller_name(r["reseller_name"]),
        })

    data["process4_narrative"] = {
        "narratives": narratives,
        "sample_maskings": sample_maskings,
    }

    # Process 5 Data: Autonomous Agent Scenarios
    tmp_dir = SQL_OUTPUT_DIR
    apr_csv = tmp_dir / "april_category_revenue.csv"
    may_csv = tmp_dir / "may_category_revenue.csv"
    june_csv = tmp_dir / "june_category_revenue.csv"

    may_agent = None
    june_agent = None
    if apr_csv.exists() and may_csv.exists():
        may_agent = run_agent("May", str(apr_csv), str(may_csv))
    if may_csv.exists() and june_csv.exists():
        june_agent = run_agent("June", str(may_csv), str(june_csv))

    data["process5_agent"] = {
        "may_scenario": may_agent,
        "june_scenario": june_agent,
    }

    return data


class IntelligenceAPIHandler(SimpleHTTPRequestHandler):
    """Serves the frontend static files and provides complete REST API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, data: Any, status: int = HTTPStatus.OK):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self._send_json(pipeline_state.get_state())
        elif path == "/api/logs":
            params = parse_qs(parsed.query)
            last_id = int(params.get("since", [0])[0])
            logs = pipeline_state.get_logs_since(last_id)
            self._send_json({"logs": logs, "total": len(pipeline_state.logs)})
        elif path == "/api/data":
            process_data = get_all_process_data()
            self._send_json(process_data)
        elif path.startswith("/api/"):
            self._send_json({"error": f"API endpoint '{path}' not found"}, status=HTTPStatus.NOT_FOUND)
        else:
            # Fall back to serving static frontend files
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get("Content-Length", 0))
        post_data = {}
        if content_len > 0:
            try:
                raw_body = self.rfile.read(content_len).decode("utf-8")
                post_data = json.loads(raw_body)
            except Exception:
                pass

        if path == "/api/run":
            regenerate = post_data.get("regenerate", False)
            if pipeline_state.is_running:
                self._send_json({"status": "already_running", "message": "Pipeline is already running"}, status=HTTPStatus.CONFLICT)
                return
            threading.Thread(target=run_full_pipeline_task, kwargs={"regenerate": regenerate}, daemon=True).start()
            self._send_json({"status": "started", "message": "Pipeline execution started in background"})

        elif path == "/api/run-step":
            step = post_data.get("step")
            if not step:
                self._send_json({"error": "Missing 'step' parameter"}, status=HTTPStatus.BAD_REQUEST)
                return
            if pipeline_state.is_running:
                self._send_json({"status": "already_running", "message": "Pipeline is already running"}, status=HTTPStatus.CONFLICT)
                return

            def step_runner():
                with pipeline_state._lock:
                    pipeline_state.is_running = True
                try:
                    run_pipeline_step(step, force_regenerate=post_data.get("regenerate", False))
                finally:
                    with pipeline_state._lock:
                        pipeline_state.is_running = False
                        pipeline_state.current_step = None

            threading.Thread(target=step_runner, daemon=True).start()
            self._send_json({"status": "started", "step": step, "message": f"Step '{step}' triggered"})

        elif path == "/api/mask":
            name = post_data.get("name", "").strip()
            if not name:
                self._send_json({"error": "Name cannot be empty"}, status=HTTPStatus.BAD_REQUEST)
                return
            masked = mask_reseller_name(name)
            self._send_json({"original": name, "masked": masked})

        elif path == "/api/generate-narrative":
            try:
                narrative = generate_narrative(post_data)
                cat = post_data.get("category", "")
                mom_pct = post_data.get("mom_pct", 0.0)
                mom_str = f"{float(mom_pct):+.2f}%" if isinstance(mom_pct, (int, float)) else "+100.00%"
                is_valid, errors = validate_narrative(narrative, cat, mom_str)
                self._send_json({
                    "narrative": narrative,
                    "is_valid": is_valid,
                    "errors": errors,
                })
            except Exception as e:
                self._send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        elif path == "/api/clear-logs":
            pipeline_state.clear_logs()
            self._send_json({"status": "cleared"})
        else:
            self._send_json({"error": f"API endpoint '{path}' not found"}, status=HTTPStatus.NOT_FOUND)


def run_cli_pipeline(regenerate: bool = False):
    """Executes the pipeline synchronously in pure CLI mode."""
    print("=" * 60)
    print("      MEESHO RESELLER INTELLIGENCE SYSTEM — CLI RUNNER     ")
    print("=" * 60)

    # Initial trigger
    run_pipeline_step("step1_data", force_regenerate=regenerate)
    run_pipeline_step("step2_sql")
    run_pipeline_step("step3_growth")
    run_pipeline_step("step4_narrative")
    run_pipeline_step("step5_agent")

    print("\n" + "=" * 60)
    print("            PIPELINE EXECUTION COMPLETED (CLI)            ")
    print("=" * 60)


def start_server(port: int = 8501, host: str = "127.0.0.1", open_browser: bool = True):
    """Launches the multi-threaded HTTP web server and serves the frontend dashboard."""
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, IntelligenceAPIHandler)
    url = f"http://{host}:{port}/"

    print("=" * 60)
    print("    MEESHO RESELLER INTELLIGENCE WEB APPLICATION SERVER    ")
    print("=" * 60)
    print(f"🚀 Server running at: {url}")
    print(f"📁 Serving frontend from: {FRONTEND_DIR}")
    print("Press Ctrl+C to terminate.")

    # Automatically run pipeline on startup if database does not exist
    if not DB_PATH.exists() or not MONTHLY_CSV.exists():
        print("\n[Auto-Start] Initializing database and SQL analytics...")
        threading.Thread(target=run_full_pipeline_task, kwargs={"regenerate": False}, daemon=True).start()

    if open_browser:
        def _open():
            time.sleep(0.8)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Meesho Reseller Intelligence server...")
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="Meesho Reseller Intelligence Main Application Runner")
    parser.add_argument("--cli", action="store_true", help="Run in command-line interface mode instead of launching web UI")
    parser.add_argument("--regenerate", action="store_true", help="Force deterministic dataset and SQLite regeneration")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind the web server to (default: 8501)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the web browser upon server start")

    args = parser.parse_args()

    if args.cli:
        run_cli_pipeline(regenerate=args.regenerate)
    else:
        start_server(port=args.port, host=args.host, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()

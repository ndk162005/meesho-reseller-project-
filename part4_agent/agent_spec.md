# Meesho Reseller Intelligence — Mock AI Agent Specification

## 1. Role & Responsibilities
The Mock AI Agent acts as an offline intelligence orchestrator. It consumes validated monthly category revenue CSV feeds, computes growth shifts, prioritizes alerts, and drafts notifications held for human approval.

It is NOT an autonomous outbound messaging client; no actual emails, SMS, WhatsApp, or Slack messages are sent.

---

## 2. Dependencies & Rule Enforcement
* **Reuses Part 2 Growth Engine**: The agent strictly imports `mom_growth()`, `is_flagged()`, `classify_growth()`, and `validate_feed()` from `part2_engine.growth_engine`. It does NOT duplicate analytics formulas or validation logic.
* **Structured Data Processing**: Operates on analytical dict/dataclass records parsed from SQL feeds.

---

## 3. Orchestration Pipeline Flow
1. Load & validate `current_month_csv` via `validate_feed()`.
   - If invalid: return `validation_status="invalid"`, `action_taken="hard_stop"`.
2. Load `previous_month_csv`.
3. Calculate MoM percentage per category via `mom_growth()`.
4. Classify category state via `classify_growth()`:
   - `abs(MoM) < 8%`: `"normal"`
   - `abs(MoM) > 8%`: `"flagged"`
   - `abs(MoM) == 8%`: `"escalated"`
5. Category State Separation:
   - `flagged_categories`: All ordinary categories with `abs(MoM) > 8%`.
   - `drafted_categories`: Top 3 ordinary flagged categories sorted by `abs(MoM)` descending.
   - `suppressed_categories`: Ordinary flagged categories beyond rank 3.
   - `escalated_categories`: Categories with `abs(MoM) == 8%` (independent of top-3 draft limits).
6. Action State: Returns `action_taken="drafted_and_held_for_approval"`.

---

## 4. JSON Output Contract
```json
{
  "run_month": "May",
  "validation_status": "valid",
  "validation_errors": [],
  "flagged_categories": [
    {"category": "Ethnic Wear", "mom_pct": 77.10, "classification": "flagged"},
    {"category": "Western Wear", "mom_pct": -23.60, "classification": "flagged"},
    {"category": "Kids Wear", "mom_pct": -23.48, "classification": "flagged"}
  ],
  "drafted_categories": [
    {"category": "Ethnic Wear", "mom_pct": 77.10, "classification": "flagged"},
    {"category": "Western Wear", "mom_pct": -23.60, "classification": "flagged"},
    {"category": "Kids Wear", "mom_pct": -23.48, "classification": "flagged"}
  ],
  "suppressed_categories": [],
  "escalated_categories": [],
  "action_taken": "drafted_and_held_for_approval"
}
```

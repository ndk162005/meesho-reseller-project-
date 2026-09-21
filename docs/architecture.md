# Meesho Reseller Intelligence — Architecture & System Design

## 1. Executive Overview
The **Meesho Reseller Intelligence Application** is a Python-based, offline-first, data-driven analytical pipeline. It ingests reseller order data, builds an SQLite relational database, computes SQL business analytics, calculates month-over-month (MoM) category growth shifts, generates narrative business reports, enforces reseller PII masking, and orchestrates mock AI agent workflows.

---

## 2. End-to-End System Architecture

```text
                    ┌───────────────────────────────┐
                    │  Deterministic Generator      │
                    │  (data/generate_dataset.py)   │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  SQLite + CSV Storage         │
                    │  (meesho_reseller.db)         │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  SQL Analytics Engine         │
                    │  (part1_sql/run_queries.py)   │
                    └───────────────┬───────────────┘
                                    │
                       monthly_category_revenue.csv
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Feed Validation & MoM Engine │
                    │  (part2_engine/growth_engine) │
                    └───────────────┬───────────────┘
                                    │
                        Structured Analytics Records
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
        ┌─────────────────────────┐   ┌─────────────────────────┐
        │ Narrative Generator     │   │ Mock AI Agent Runner    │
        │ & Privacy Masking       │   │ (part4_agent/runner.py) │
        │ (part3_narrative)       │   └────────────┬────────────┘
        └─────────────────────────┘                │
                                                   ▼
                                      ┌─────────────────────────┐
                                      │  Structured JSON &      │
                                      │  Human Approval Draft   │
                                      └─────────────────────────┘
```

---

## 3. Core Component Responsibilities

### Data Layer (`data/`)
- Deterministically generates 24 resellers across 4 regions and 900 orders across April, May, and June.
- Guarantees RS024 has zero orders.
- Stores dataset in `resellers.csv`, `orders.csv`, and SQLite database `meesho_reseller.db`.

### SQL Analytics Layer (`part1_sql/`)
- Aggregates monthly category revenues into 15 rows.
- Computes regional revenues, top 5 resellers by delivered revenue, zero-order resellers, `COUNT(*)` vs `COUNT(order_id)` demonstrations, and June delivered AOV.

### Growth Engine & Validation (`part2_engine/`)
- Single source of truth for Month-over-Month calculation, zero-baseline handling (`new_revenue`), 3-state classification (`normal`, `flagged`, `escalated` at exact ±8%), and feed validation.

### Narrative System & Privacy Masking (`part3_narrative/`)
- Converts structured analytics records into Context → Insight → Implication business text.
- Enforces strict separation between empirical facts and speculative hypotheses.
- Protects reseller PII using deterministic hash masking (`Reseller RXXX`).

### Mock AI Agent (`part4_agent/`)
- Imports and reuses Part 2 logic to validate feeds and classify category shifts.
- Classifies category states into 4 logical lists: `flagged_categories`, `drafted_categories` (top 3 by `abs(mom_pct)` descending), `suppressed_categories`, and `escalated_categories`.
- Returns valid structured JSON held for human approval without sending real outbound communications.

---

## 4. Key Design Decisions & Constraints
- **Offline-First**: Zero external API dependencies, zero cloud services, zero external network calls.
- **No API Keys**: Fully executable on any local machine without credentials.
- **Deterministic & Reproducible**: Fixed seeds ensure repeatable analytics and test outputs.
- **Strict Logic Reuse**: Part 4 agent orchestrates rather than reimplementing Part 2 formulas.

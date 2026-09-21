# Meesho Reseller Intelligence Application

An offline-first, deterministic Python intelligence pipeline for reseller analytics, month-over-month growth classification, privacy masking, business narrative generation, and mock AI agent orchestration.

---

## 1. Quick Start

### Installation
Clone or extract the project, then install minimal dependencies:
```bash
python -m pip install -r requirements.txt
```

### Launch Interactive Web Application & Dashboard UI
To launch the executive web dashboard (automatically opens in your browser at `http://127.0.0.1:8501/`):
```bash
python main.py
```
Options:
- `python main.py --port 8000` (custom port)
- `python main.py --no-browser` (start server without auto-opening browser)
- `python main.py --cli` (run full pipeline directly in terminal)
- `python main.py --cli --regenerate` (force regenerate dataset and run in terminal)

### Run Pipeline in CLI Mode
To run the end-to-end pipeline in terminal mode:
```bash
python main.py --cli
# Or legacy script:
python run_pipeline.py
```

To force dataset regeneration and re-run analytics:
```bash
python main.py --cli --regenerate
```

### Run Test Suite
Run unit, part-specific, and integration tests with pytest:
```bash
python -m pytest
```

---

## 2. Project Architecture & Components

```text
meesho-reseller-intelligence/
├── README.md
├── requirements.txt
├── .gitignore
├── main.py                   # Unified runner (Web UI server & CLI modes)
├── run_pipeline.py           # Legacy terminal runner
├── frontend/                 # Interactive Dashboard Web UI
│   ├── index.html            # Single-page executive UI
│   ├── styles.css            # Meesho-themed design system
│   └── app.js                # State manager, log streaming & visualizers
├── data/
│   ├── generate_dataset.py       # Deterministic generator (24 resellers, 900 orders)
│   ├── resellers.csv             # Reseller master data
│   ├── orders.csv                # Order transactional data
│   └── meesho_reseller.db        # SQLite database
├── part1_sql/
│   ├── queries.sql               # SQL queries for analytics & LEFT JOIN demos
│   ├── run_queries.py            # SQL runner producing CSV outputs
│   └── output/                   # Generated SQL analytics CSVs
├── part2_engine/
│   ├── growth_engine.py          # MoM calculation, zero-baseline, 3-state classification
│   └── test_growth_engine.py     # Unit tests for growth engine
├── part3_narrative/
│   ├── prompt_pack.md            # Narrative rules (Context -> Insight -> Implication)
│   ├── masking.py                # Deterministic reseller PII hash masking
│   ├── narrative_generator.py    # Structured narrative builder
│   └── narrative_validator.py    # Narrative format validator
├── part4_agent/
│   ├── agent_spec.md             # Mock agent specifications
│   ├── agent_models.py           # Dataclasses for agent state
│   ├── mock_agent_runner.py      # Agent runner reusing Part 2 logic
│   └── test_agent.py             # Agent orchestration tests
├── tests/
│   └── integration/
│       └── test_pipeline.py      # Full integration tests
└── docs/
    └── architecture.md           # Deep-dive system architecture
```

---

## 3. Key Design Highlights
* **Offline & Free of External Dependencies**: No API keys, no network calls, no external LLM APIs.
* **Deterministic & Reproducible**: Seeded generator reproduces exact acceptance targets.
* **Strict Logic Reuse**: Part 4 agent imports Part 2 functions (`mom_growth`, `classify_growth`, `validate_feed`) directly without code duplication.
* **Exact Boundary Escalation**: `abs(MoM) == 8.0%` is classified as `escalated` and kept distinct from ordinary `suppressed` categories.
* **Privacy Aware**: Deterministic hash masking replaces PII names (`Reseller RXXX`).

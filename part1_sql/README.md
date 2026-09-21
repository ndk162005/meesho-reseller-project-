# Part 1 — SQL Analytics

This module executes SQL analytics on the SQLite database `data/meesho_reseller.db`.

## Queries Included
1. **Monthly Category Revenue**: Aggregates revenue and order count for April, May, and June across 5 categories.
2. **Regional Revenue**: Aggregates total revenue and order count across 4 geographic regions.
3. **Top 5 Resellers**: Identifies top resellers by delivered revenue.
4. **Zero-Order Resellers & LEFT JOIN COUNT Demonstration**: Identifies resellers with zero orders (RS024) and contrasts `COUNT(*)` (counts NULL row) vs `COUNT(order_id)` (correctly yields 0).
5. **June Delivered AOV**: Calculates Average Order Value for delivered orders in June.

## Running SQL Analytics
```bash
python part1_sql/run_queries.py
```
Output files will be generated under `part1_sql/output/`.

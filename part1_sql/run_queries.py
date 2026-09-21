import sqlite3
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DB_PATH = PROJECT_DIR / "data" / "meesho_reseller.db"
OUTPUT_DIR = BASE_DIR / "output"

def run_sql_analytics():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database missing at {DB_PATH}. Run data/generate_dataset.py first.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Database found. Running SQL analytics...")

    # Query 1: Monthly Category Revenue
    q1 = """
    SELECT 
        CASE substr(order_date, 6, 2)
            WHEN '04' THEN 'April'
            WHEN '05' THEN 'May'
            WHEN '06' THEN 'June'
        END AS month,
        category,
        ROUND(SUM(order_value), 2) AS revenue,
        COUNT(order_id) AS n_orders
    FROM orders
    GROUP BY month, category
    ORDER BY 
        CASE month
            WHEN 'April' THEN 1
            WHEN 'May' THEN 2
            WHEN 'June' THEN 3
        END,
        category;
    """
    cursor.execute(q1)
    rows1 = cursor.fetchall()
    with open(OUTPUT_DIR / "monthly_category_revenue.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "category", "revenue", "n_orders"])
        writer.writerows(rows1)
    print("Monthly category revenue generated.")

    # Query 2: Regional Revenue
    q2 = """
    SELECT 
        r.region,
        ROUND(SUM(o.order_value), 2) AS revenue,
        COUNT(o.order_id) AS n_orders
    FROM resellers r
    LEFT JOIN orders o ON r.reseller_id = o.reseller_id
    GROUP BY r.region
    ORDER BY revenue DESC;
    """
    cursor.execute(q2)
    rows2 = cursor.fetchall()
    with open(OUTPUT_DIR / "region_revenue.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["region", "revenue", "n_orders"])
        writer.writerows(rows2)
    print("Regional revenue generated.")

    # Query 3: Top Resellers
    q3 = """
    SELECT 
        r.reseller_id,
        r.reseller_name,
        r.region,
        ROUND(SUM(o.order_value), 2) AS delivered_revenue,
        COUNT(o.order_id) AS delivered_orders
    FROM resellers r
    JOIN orders o ON r.reseller_id = o.reseller_id
    WHERE o.order_status = 'Delivered'
    GROUP BY r.reseller_id, r.reseller_name, r.region
    ORDER BY delivered_revenue DESC
    LIMIT 5;
    """
    cursor.execute(q3)
    rows3 = cursor.fetchall()
    with open(OUTPUT_DIR / "top_resellers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["reseller_id", "reseller_name", "region", "delivered_revenue", "delivered_orders"])
        writer.writerows(rows3)
    print("Top 5 resellers generated.")

    # Query 4a: Zero Order Resellers
    q4a = """
    SELECT 
        r.reseller_id,
        r.reseller_name,
        r.region
    FROM resellers r
    LEFT JOIN orders o ON r.reseller_id = o.reseller_id
    GROUP BY r.reseller_id, r.reseller_name, r.region
    HAVING COUNT(o.order_id) = 0;
    """
    cursor.execute(q4a)
    rows4a = cursor.fetchall()
    with open(OUTPUT_DIR / "zero_order_resellers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["reseller_id", "reseller_name", "region"])
        writer.writerows(rows4a)

    # Query 4b: COUNT(*) vs COUNT(order_id) Demo
    q4b = """
    SELECT 
        r.reseller_id,
        r.reseller_name,
        COUNT(*) AS count_star,
        COUNT(o.order_id) AS count_order_id
    FROM resellers r
    LEFT JOIN orders o ON r.reseller_id = o.reseller_id
    GROUP BY r.reseller_id, r.reseller_name
    ORDER BY count_order_id ASC, r.reseller_id ASC;
    """
    cursor.execute(q4b)
    rows4b = cursor.fetchall()
    with open(OUTPUT_DIR / "zero_order_count_demo.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["reseller_id", "reseller_name", "count_star", "count_order_id"])
        writer.writerows(rows4b)
    print("Zero-order analysis generated.")

    # Query 5: June Delivered AOV
    q5 = """
    SELECT 
        'June' AS month,
        ROUND(SUM(order_value), 2) AS delivered_revenue,
        COUNT(order_id) AS delivered_orders,
        ROUND(SUM(order_value) / COUNT(order_id), 2) AS aov
    FROM orders
    WHERE order_date LIKE '2024-06%'
      AND order_status = 'Delivered';
    """
    cursor.execute(q5)
    rows5 = cursor.fetchall()
    with open(OUTPUT_DIR / "june_aov.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "delivered_revenue", "delivered_orders", "aov"])
        writer.writerows(rows5)
    print("June AOV generated.")

    conn.close()
    print("Part 1 completed successfully.")

if __name__ == "__main__":
    run_sql_analytics()

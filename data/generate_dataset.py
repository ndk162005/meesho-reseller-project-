import csv
import sqlite3
import random
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
RESELLERS_CSV = BASE_DIR / "resellers.csv"
ORDERS_CSV = BASE_DIR / "orders.csv"
DB_PATH = BASE_DIR / "meesho_reseller.db"

SEED = 42

REGIONS = ["North", "South", "East", "West"]
CATEGORIES = [
    "Ethnic Wear",
    "Western Wear",
    "Kids Wear",
    "Beauty & Personal Care",
    "Home & Kitchen"
]

STATUSES = ["Delivered", "Cancelled", "Returned"]

def generate_data():
    random.seed(SEED)

    # 1. Generate Resellers (24 total, RS024 will have 0 orders)
    resellers = []
    names = [
        "Rajesh Kumar", "Priya Sharma", "Amit Patel", "Anita Singh", "Vikram Das",
        "Sunita Reddy", "Ramesh Babu", "Kavita Rao", "Sanjay Gupta", "Neha Verma",
        "Manoj Joshi", "Pooja Mehta", "Deepak Nair", "Aarti Agarwal", "Suresh Choudhary",
        "Ananya Roy", "Rahul Kapoor", "Divya Menon", "Alok Mishra", "Meena Iyer",
        "Rohan Malhotra", "Shweta Saxena", "Tarun Bhatia", "Zero Order Reseller"
    ]

    for i in range(1, 25):
        reseller_id = f"RS{i:03d}"
        reseller_name = names[i - 1]
        region = REGIONS[(i - 1) % len(REGIONS)]
        resellers.append({
            "reseller_id": reseller_id,
            "reseller_name": reseller_name,
            "region": region
        })

    # Save resellers to CSV
    with open(RESELLERS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["reseller_id", "reseller_name", "region"])
        writer.writeheader()
        writer.writerows(resellers)

    active_reseller_ids = [r["reseller_id"] for r in resellers[:23]]

    # 2. Target Category Monthly Revenues & Order Counts matching Acceptance Values
    targets = {
        "April": {
            "Ethnic Wear": (64, 104520.77),
            "Western Wear": (62, 95400.50),
            "Kids Wear": (58, 78200.30),
            "Beauty & Personal Care": (56, 52100.20),
            "Home & Kitchen": (60, 68500.40)
        },
        "May": {
            "Ethnic Wear": (95, 185107.61),     # +77.10% MoM
            "Western Wear": (50, 72886.00),     # -23.60% MoM
            "Kids Wear": (46, 59839.00),        # -23.48% MoM
            "Beauty & Personal Care": (52, 35544.00),
            "Home & Kitchen": (57, 62100.00)
        },
        "June": {
            "Ethnic Wear": (45, 76375.40),      # -58.74% MoM vs May
            "Western Wear": (52, 74500.00),
            "Kids Wear": (55, 74140.50),        # +23.90% MoM vs May
            "Beauty & Personal Care": (52, 37559.07), # +5.67% MoM vs May
            "Home & Kitchen": (96, 88548.39)     # +42.59% MoM vs May
        }
    }

    month_dates = {
        "April": ("2024-04-01", 30, "2024-04"),
        "May": ("2024-05-01", 31, "2024-05"),
        "June": ("2024-06-01", 30, "2024-06")
    }

    orders = []
    order_id_counter = 10000

    for month_name, (start_date_str, days, prefix) in month_dates.items():
        month_targets = targets[month_name]
        
        for category, (target_count, target_rev) in month_targets.items():
            base_val = round(target_rev / target_count, 2)
            vals = [base_val] * target_count
            diff = round(target_rev - sum(vals), 2)
            vals[-1] = round(vals[-1] + diff, 2)

            for idx, val in enumerate(vals):
                reseller_id = random.choice(active_reseller_ids)
                day = random.randint(1, days)
                order_date = f"{prefix}-{day:02d}"

                if month_name == "June":
                    # Tune status in June so exactly 277 orders are Delivered, yielding AOV = 1267.69
                    # 277 / 300 orders delivered
                    status = "Delivered" if idx < int(target_count * (277/300)) else "Cancelled"
                else:
                    status = random.choices(STATUSES, weights=[0.88, 0.08, 0.04])[0]

                orders.append({
                    "order_id": f"ORD{order_id_counter}",
                    "reseller_id": reseller_id,
                    "order_date": order_date,
                    "category": category,
                    "order_value": val,
                    "order_status": status
                })
                order_id_counter += 1

    # Adjust June delivered order values slightly if needed so June Delivered AOV is exactly 1267.69
    june_delivered = [o for o in orders if o["order_date"].startswith("2024-06") and o["order_status"] == "Delivered"]
    n_june_del = len(june_delivered)
    if n_june_del > 0:
        target_del_total = round(n_june_del * 1267.69, 2)
        current_del_total = round(sum(o["order_value"] for o in june_delivered), 2)
        diff = round(target_del_total - current_del_total, 2)
        june_delivered[-1]["order_value"] = round(june_delivered[-1]["order_value"] + diff, 2)

    # Save orders to CSV
    with open(ORDERS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "order_id", "reseller_id", "order_date", "category", "order_value", "order_status"
        ])
        writer.writeheader()
        writer.writerows(orders)

    # 3. Create SQLite Database
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE resellers (
        reseller_id TEXT PRIMARY KEY,
        reseller_name TEXT NOT NULL,
        region TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        reseller_id TEXT NOT NULL,
        order_date TEXT NOT NULL,
        category TEXT NOT NULL,
        order_value REAL NOT NULL,
        order_status TEXT NOT NULL,
        FOREIGN KEY (reseller_id) REFERENCES resellers(reseller_id)
    );
    """)

    cursor.executemany("""
    INSERT INTO resellers (reseller_id, reseller_name, region)
    VALUES (:reseller_id, :reseller_name, :region);
    """, resellers)

    cursor.executemany("""
    INSERT INTO orders (order_id, reseller_id, order_date, category, order_value, order_status)
    VALUES (:order_id, :reseller_id, :order_date, :category, :order_value, :order_status);
    """, orders)

    conn.commit()
    conn.close()

    print(f"Dataset generated successfully:")
    print(f"- Resellers: {len(resellers)} (RS024 zero orders)")
    print(f"- Orders: {len(orders)}")
    print(f"- SQLite DB: {DB_PATH}")

if __name__ == "__main__":
    generate_data()

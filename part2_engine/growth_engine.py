import csv
from pathlib import Path
from typing import Tuple, List, Union

REQUIRED_COLUMNS = {"month", "category", "revenue", "n_orders"}
REQUIRED_CATEGORIES = {
    "Ethnic Wear",
    "Western Wear",
    "Kids Wear",
    "Beauty & Personal Care",
    "Home & Kitchen"
}

def mom_growth(previous: float, current: float) -> Union[float, str]:
    """
    Calculate Month-over-Month growth percentage.
    Formula: ((current - previous) / previous) * 100

    Zero-Baseline Handling:
    - previous == 0 and current == 0 -> 0.0
    - previous == 0 and current > 0  -> 'new_revenue' (no ZeroDivisionError, no infinity)
    """
    try:
        prev_val = float(previous)
        curr_val = float(current)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid monetary values for MoM growth: previous={previous}, current={current}")

    if prev_val == 0.0:
        if curr_val == 0.0:
            return 0.0
        return "new_revenue"

    growth = ((curr_val - prev_val) / prev_val) * 100.0
    return round(growth, 2)

def is_flagged(mom_pct: Union[float, str], threshold: float = 8.0) -> bool:
    """
    Preserved function signature.
    Returns True if abs(mom_pct) > threshold, False otherwise.
    Note: Exact boundary (abs(mom_pct) == threshold) returns False (escalated state).
    """
    if mom_pct == "new_revenue":
        return True

    if not isinstance(mom_pct, (int, float)):
        return False

    return abs(float(mom_pct)) > float(threshold)

def classify_growth(mom_pct: Union[float, str], threshold: float = 8.0) -> str:
    """
    Three-state growth classification based on abs(mom_pct):
    - abs(mom_pct) < 8.0  -> 'normal'
    - abs(mom_pct) > 8.0  -> 'flagged'
    - abs(mom_pct) == 8.0 -> 'escalated'
    Special zero baseline state ('new_revenue') is classified as 'flagged'.
    """
    if mom_pct == "new_revenue":
        return "flagged"

    try:
        val = abs(float(mom_pct))
        thresh = float(threshold)
    except (ValueError, TypeError):
        return "normal"

    # Floating point comparison with tolerance
    if abs(val - thresh) < 1e-6:
        return "escalated"
    elif val > thresh:
        return "flagged"
    else:
        return "normal"

def validate_feed(csv_path: Union[str, Path]) -> Tuple[bool, List[str]]:
    """
    Validate monthly category revenue CSV feed.
    Checks:
    - File exists and is non-empty
    - Header contains required columns
    - Category values present & valid
    - Revenue is numeric and non-negative
    - n_orders is non-negative integer
    - All 5 required categories present
    Returns (True, []) or (False, [error_messages])
    """
    path = Path(csv_path)
    if not path.exists():
        return False, [f"File not found: {path}"]

    errors = []
    found_categories = set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return False, ["CSV file is empty or missing header."]

            headers = set(reader.fieldnames)
            missing_cols = REQUIRED_COLUMNS - headers
            if missing_cols:
                return False, [f"Missing required columns: {sorted(list(missing_cols))}"]

            for row_idx, row in enumerate(reader, start=2):
                cat = row.get("category", "").strip()
                if not cat:
                    errors.append(f"Row {row_idx}: Missing category name.")
                else:
                    found_categories.add(cat)

                rev_str = row.get("revenue", "").strip()
                try:
                    rev = float(rev_str)
                    if rev < 0:
                        errors.append(f"Row {row_idx}: Revenue cannot be negative ({rev}).")
                except ValueError:
                    errors.append(f"Row {row_idx}: Invalid numeric revenue '{rev_str}'.")

                n_str = row.get("n_orders", "").strip()
                try:
                    n_ord = int(n_str)
                    if n_ord < 0:
                        errors.append(f"Row {row_idx}: Order count cannot be negative ({n_ord}).")
                except ValueError:
                    errors.append(f"Row {row_idx}: Invalid order count '{n_str}'.")

    except Exception as e:
        return False, [f"Failed to parse CSV file: {str(e)}"]

    missing_cats = REQUIRED_CATEGORIES - found_categories
    if missing_cats:
        errors.append(f"Missing required categories in feed: {sorted(list(missing_cats))}")

    if errors:
        return False, errors

    return True, []

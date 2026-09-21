from typing import Dict, Any
from part3_narrative.masking import mask_reseller_name

def generate_narrative(record: Dict[str, Any]) -> str:
    """
    Generate controlled business narrative from analytical data record.
    record fields:
    - category (str)
    - previous_month (str)
    - current_month (str)
    - previous_revenue (float)
    - current_revenue (float)
    - mom_pct (float/str)
    - top_reseller (str, optional)
    """
    category = record.get("category", "Unknown Category")
    prev_month = record.get("previous_month", "Previous Month")
    curr_month = record.get("current_month", "Current Month")
    prev_rev = record.get("previous_revenue", 0.0)
    curr_rev = record.get("current_revenue", 0.0)
    mom_pct = record.get("mom_pct", 0.0)
    top_reseller = record.get("top_reseller", None)

    # Format numeric representation
    if mom_pct == "new_revenue":
        growth_str = "new revenue introduction"
        mom_val_str = "+100.00% (New Baseline)"
    else:
        growth_sign = "+" if float(mom_pct) >= 0 else ""
        growth_str = f"{growth_sign}{float(mom_pct):.2f}%"
        mom_val_str = growth_str

    reseller_text = ""
    if top_reseller:
        masked_reseller = mask_reseller_name(top_reseller)
        reseller_text = f" Top contributor was masked as {masked_reseller}."

    # Context
    context = (
        f"CONTEXT: For the category '{category}', revenue in {prev_month} was Rs. {prev_rev:,.2f} "
        f"and in {curr_month} was Rs. {curr_rev:,.2f}.{reseller_text}"
    )

    # Insight
    direction = "increased" if (mom_pct == "new_revenue" or float(mom_pct) >= 0) else "decreased"
    insight = (
        f"INSIGHT: {category} revenue {direction} by {mom_val_str} Month-over-Month in {curr_month} "
        f"compared to {prev_month}."
    )

    # Implication (Strictly Framed Hypothesis)
    if direction == "increased":
        hypothesis = (
            f"IMPLICATION (HYPOTHESIS): The revenue surge in {category} may indicate heightened consumer demand, "
            f"effective seasonal promotions, or expanded reseller catalog listings."
        )
    else:
        hypothesis = (
            f"IMPLICATION (HYPOTHESIS): The revenue reduction in {category} suggests possible supply constraints, "
            f"post-peak seasonal normalization, or increased competition in the category."
        )

    return f"{context}\n{insight}\n{hypothesis}"

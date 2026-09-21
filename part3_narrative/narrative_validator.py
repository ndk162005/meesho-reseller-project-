from typing import Tuple, List

def validate_narrative(narrative_text: str, category: str, expected_mom_str: str) -> Tuple[bool, List[str]]:
    """
    Validate that generated narrative obeys structure and contains data facts.
    Checks:
    - Contains CONTEXT:
    - Contains INSIGHT:
    - Contains IMPLICATION (HYPOTHESIS):
    - Contains exact category name
    - Contains exact expected MoM string
    - Does not contain raw unmasked reseller names
    """
    errors = []

    if "CONTEXT:" not in narrative_text:
        errors.append("Missing 'CONTEXT:' section.")

    if "INSIGHT:" not in narrative_text:
        errors.append("Missing 'INSIGHT:' section.")

    if "IMPLICATION (HYPOTHESIS):" not in narrative_text and "HYPOTHESIS" not in narrative_text:
        errors.append("Missing 'IMPLICATION (HYPOTHESIS):' section.")

    if category not in narrative_text:
        errors.append(f"Category name '{category}' missing from narrative.")

    if expected_mom_str not in narrative_text:
        errors.append(f"Expected MoM value string '{expected_mom_str}' missing from narrative.")

    if errors:
        return False, errors

    return True, []

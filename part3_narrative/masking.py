import hashlib

_MASK_CACHE = {}

def mask_reseller_name(raw_name: str) -> str:
    """
    Deterministic masking of reseller PII names into anonymous identifiers.
    Example: 'Rajesh Kumar' -> 'Reseller R001'
    """
    if not raw_name or not isinstance(raw_name, str):
        return "Reseller R000"

    clean_name = raw_name.strip()
    if clean_name in _MASK_CACHE:
        return _MASK_CACHE[clean_name]

    # Deterministic hash to generate 3-digit index
    hash_val = int(hashlib.md5(clean_name.encode("utf-8")).hexdigest(), 16)
    reseller_index = (hash_val % 999) + 1
    masked_id = f"Reseller R{reseller_index:03d}"
    _MASK_CACHE[clean_name] = masked_id
    return masked_id

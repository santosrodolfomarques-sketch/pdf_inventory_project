from __future__ import annotations

import hashlib
from typing import Any

def stable_hash_id(namespace: str, *parts: Any, length: int = 16) -> str:
    raw = "|".join("" if part is None else str(part).strip() for part in parts)
    digest = hashlib.sha1(f"{namespace}|{raw}".encode("utf-8")).hexdigest()
    return f"{namespace}_{digest[:length]}"

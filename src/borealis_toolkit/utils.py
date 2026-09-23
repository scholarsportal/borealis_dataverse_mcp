from __future__ import annotations

import re
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_boolean_query(query: str) -> str:
    return re.sub(r"\b(and|or|not)\b", lambda m: m.group(0).upper(), query, flags=re.IGNORECASE)


def normalize_identifier(identifier: str) -> tuple[str, bool]:
    value = identifier.strip()
    if value.startswith("http") and "doi.org/" in value:
        value = value.split("doi.org/", 1)[1]
    if value.isdigit():
        return value, False
    if not value.startswith("doi:"):
        value = f"doi:{value}"
    return value, True


def human_size(size: int) -> str:
    if size < 1024:
        return f"{size} bytes"
    if size < 1024**2:
        return f"{size / 1024:.1f} KB"
    if size < 1024**3:
        return f"{size / 1024**2:.1f} MB"
    return f"{size / 1024**3:.2f} GB"

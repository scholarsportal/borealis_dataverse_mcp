from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    api_base_url: str = os.getenv("BOREALIS_API_BASE_URL", "https://borealisdata.ca/api")
    api_key: str = os.getenv("BOREALIS_API_KEY", "")
    request_timeout_seconds: float = float(os.getenv("BOREALIS_TIMEOUT_SECONDS", "30"))
    max_file_bytes: int = int(os.getenv("BOREALIS_MAX_FILE_BYTES", str(25 * 1024 * 1024)))
    default_max_lines: int = int(os.getenv("BOREALIS_DEFAULT_MAX_LINES", "100"))

    @property
    def authentication_configured(self) -> bool:
        return len(self.api_key.strip()) > 10

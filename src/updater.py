from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateResult:
    ok: bool
    message: str
    latest_version: Optional[str] = None
    current_version: Optional[str] = None


def check_update(version_url: str, current_version: str, timeout_s: int = 5) -> UpdateResult:
    return UpdateResult(False, 'Update URL is not configured.', None, current_version)

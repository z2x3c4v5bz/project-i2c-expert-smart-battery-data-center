from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateResult:
    ok: bool
    message: str
    latest_version: Optional[str] = None
    current_version: Optional[str] = None


def check_update(version_url: str, current_version: str, timeout_s: int = 5) -> UpdateResult:
    """Check update from a GitHub raw URL (or any HTTPS URL).

    Expected JSON format:
    {
      "latest": "1.2.3",
      "notes": "...",
      "url": "https://..."
    }

    This function is intentionally simple to comply with 'no internet access except update check'.
    """
    if not version_url:
        return UpdateResult(False, 'Update URL is not configured.', None, current_version)

    try:
        req = urllib.request.Request(version_url, headers={'User-Agent': 'I2C-Expert-SBDC'})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = resp.read().decode('utf-8', errors='replace')
        obj = json.loads(data)
        latest = str(obj.get('latest', '')).strip()
        notes = str(obj.get('notes', '')).strip()
        url = str(obj.get('url', '')).strip()

        if not latest:
            return UpdateResult(False, 'Invalid update payload: missing latest.', None, current_version)

        if latest == current_version:
            return UpdateResult(True, 'You are up to date.', latest, current_version)

        msg = f"New version available: {latest}.\n\nNotes:\n{notes}\n\nURL: {url}"
        return UpdateResult(True, msg, latest, current_version)

    except Exception as e:
        return UpdateResult(False, f'Update check failed: {e}', None, current_version)

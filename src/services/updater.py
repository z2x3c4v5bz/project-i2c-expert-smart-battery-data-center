from __future__ import annotations

import json
import urllib.error
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
    if not version_url:
        return UpdateResult(False, 'Update URL is not configured.', None, current_version)

    try:
        with urllib.request.urlopen(version_url, timeout=timeout_s) as response:
            if response.status != 200:
                return UpdateResult(False, f'Failed to fetch update info: HTTP {response.status}', None, current_version)
            body = response.read().decode('utf-8')
            data = json.loads(body)
    except urllib.error.URLError as exc:
        return UpdateResult(False, f'Failed to fetch update info: {exc}', None, current_version)
    except json.JSONDecodeError as exc:
        return UpdateResult(False, f'Invalid update info format: {exc}', None, current_version)
    except Exception as exc:
        return UpdateResult(False, f'Error checking update: {exc}', None, current_version)

    latest = data.get('latest')
    url = data.get('url')
    notes = data.get('notes')
    if not latest:
        return UpdateResult(False, 'Update info is missing latest version.', None, current_version)

    if latest == current_version:
        return UpdateResult(True, 'You are running the latest version.', latest, current_version)

    message_parts = [f'New version available: {latest}']
    if url:
        message_parts.append(f'Check: {url}')
    if notes:
        message_parts.append(f'Notes:\n{notes}')
    return UpdateResult(True, '\n'.join(message_parts), latest, current_version)

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List


def safe_int(s: str, base: int = 10, default: int = 0) -> int:
    """Parse int safely.

    Args:
        s: input string.
        base: numeric base.
        default: fallback value.

    Returns:
        Parsed integer or default.
    """
    try:
        return int(s, base)
    except Exception:
        return default


def strip_us_unit(ts: str) -> str:
    """Remove trailing 'us' (microseconds) from timestamp string."""
    return ts.replace('us', '').strip()


def format_time_us_to_hhmmssus(us: int) -> str:
    """Format microsecond timestamp into hh:mm:ss:us."""
    if us < 0:
        us = 0
    total_seconds, micro = divmod(us, 1_000_000)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{micro:06d}"


def normalize_hex_token(tok: str) -> tuple[str, bool]:
    """Normalize hex byte token and detect NACK marker (#).

    Returns:
        (hex_byte_upper, is_nack)
    """
    tok = tok.strip()
    is_nack = tok.endswith('#')
    tok = tok.replace('#', '')
    return tok.upper(), is_nack


@dataclass
class ParsedRecord:
    # Display fields
    time_us: Optional[int]
    rw: str
    device_address: str
    command_code: str
    function: str
    value_str: str
    unit: str
    data_raw: str

    # Internal
    is_valid: bool
    is_nack: bool
    bytes_le: List[int]

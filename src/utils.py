from __future__ import annotations

from typing import Union


def safe_int(s: str, base: int = 10, default: int = 0) -> int:
    """Parse int safely."""
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
    """Normalize hex byte token and detect NACK marker (#)."""
    tok = tok.strip()
    is_nack = tok.endswith('#')
    tok = tok.replace('#', '')
    return tok.upper(), is_nack


def canonical_hex(value: Union[int, str], width: int = 2) -> str:
    """Return the canonical ``0xHH`` form for an int or hex string.

    Accepts an integer, a bare hex string (``"2d"``) or a prefixed one
    (``"0x2D"``). Raises ``ValueError`` on anything that is not valid hex,
    mirroring ``int(x, 16)`` so existing try/except callers keep working.
    This is the single source of truth for command-code normalization.
    """
    if isinstance(value, int):
        v = value
    else:
        s = str(value).strip()
        if s.lower().startswith('0x'):
            s = s[2:]
        v = int(s, 16)
    return f"0x{v:0{width}X}"

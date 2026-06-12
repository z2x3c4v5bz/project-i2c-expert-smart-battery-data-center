from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..models.record import ParsedRecord
from ..utils import canonical_hex

# Search field identifiers (kept short to match the menu wiring).
FIELD_CMD = 'cmd'
FIELD_RAW = 'raw'
FIELD_RW = 'rw'


@dataclass
class SearchSpec:
    field: str   # FIELD_CMD | FIELD_RAW | FIELD_RW
    query: str


def matches(spec: SearchSpec, record: ParsedRecord) -> bool:
    """True if ``record`` satisfies the search ``spec``."""
    q = spec.query.strip()

    if spec.field == FIELD_CMD:
        if not record.is_valid:
            return False
        try:
            cc = canonical_hex(record.command_code)
        except ValueError:
            cc = (record.command_code or '').upper()
        try:
            qn = canonical_hex(q)
        except ValueError:
            qn = q.upper()
        return cc.upper() == qn.upper()

    if spec.field == FIELD_RW:
        return (record.rw or '').upper() == q.upper()

    return q.lower() in (record.data_raw or '').lower()


def find(spec: SearchSpec, visible: List[int], records: List[ParsedRecord],
         start_pos: int, direction: int) -> Optional[int]:
    """Find the next match within the visible view.

    ``start_pos`` is a position into ``visible`` (the currently selected row);
    the scan begins one step away in ``direction`` (+1 / -1) and wraps around.
    Returns the matching position into ``visible``, or ``None`` if no match.
    """
    n = len(visible)
    if n == 0:
        return None

    pos = (start_pos + direction) % n
    for _ in range(n):
        if matches(spec, records[visible[pos]]):
            return pos
        pos = (pos + direction) % n
    return None

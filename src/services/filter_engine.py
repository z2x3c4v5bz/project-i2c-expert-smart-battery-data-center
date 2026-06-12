from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..models.record import ParsedRecord
from ..utils import canonical_hex


@dataclass
class FilterSpec:
    """A pure description of the active table filter.

    ``device_address`` is compared case-insensitively. ``command_code`` is
    expected in canonical ``0xHH`` form (build it with ``canonical_hex``);
    empty strings mean "no constraint on this field".
    """

    device_address: str = ''
    command_code: str = ''
    hide_invalid: bool = False


def apply(spec: FilterSpec, records: List[ParsedRecord]) -> List[int]:
    """Return the indices of records that pass ``spec``."""
    dev = (spec.device_address or '').strip().upper()
    cmd = (spec.command_code or '').strip()

    out: List[int] = []
    for i, r in enumerate(records):
        if spec.hide_invalid and not r.is_valid:
            continue
        if dev and (r.device_address or '').upper() != dev:
            continue
        if cmd:
            if not r.is_valid:
                continue
            try:
                cc = canonical_hex(r.command_code)
            except ValueError:
                cc = ''
            if cc != cmd:
                continue
        out.append(i)
    return out

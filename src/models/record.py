from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ParsedRecord:
    """One decoded I2C transaction.

    Carries both the raw bytes (``bytes_le``, low->high order, for numeric
    decoding) and the enriched display fields (``function``, ``value_str``,
    ``unit``) the table renders. ``is_valid`` is the first-class flag the rest
    of the app uses to decide whether the decoded fields are meaningful.
    """

    time_us: Optional[int]
    rw: str
    device_address: str
    command_code: str
    function: str
    value_str: str
    unit: str
    data_raw: str
    is_valid: bool
    is_nack: bool
    bytes_le: List[int]  # low->high order

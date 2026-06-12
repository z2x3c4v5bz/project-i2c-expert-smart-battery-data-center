from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .models.record import ParsedRecord
from .models.sbs import SbsConfig
from .services.filter_engine import FilterSpec
from .services.log_parser import ParseOptions


@dataclass
class AppState:
    """Single source of truth for the main window's data.

    UI components receive a reference to this object and read/write through it,
    instead of scattering the same state across many ``App`` instance vars.
    """

    config: Optional[SbsConfig] = None
    config_path: Optional[str] = None
    log_path: Optional[str] = None
    all_records: List[ParsedRecord] = field(default_factory=list)
    visible_indices: List[int] = field(default_factory=list)
    filter_spec: FilterSpec = field(default_factory=FilterSpec)
    parse_options: ParseOptions = field(default_factory=ParseOptions)
    selected_index: Optional[int] = None

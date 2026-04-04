from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple

from matplotlib.figure import Figure

from .utils import ParsedRecord


@dataclass
class PlotSeries:
    name: str
    unit: str
    x: List[float]
    y: List[float]


def build_series(records: List[ParsedRecord], targets: Dict[str, Tuple[str, str]]) -> List[PlotSeries]:
    series_map: Dict[str, PlotSeries] = {}
    for fn, (sname, unit) in targets.items():
        series_map[fn] = PlotSeries(name=sname, unit=unit, x=[], y=[])

    t0 = None
    for r in records:
        if not r.is_valid or r.time_us is None:
            continue
        if t0 is None:
            t0 = r.time_us
        if r.function in series_map:
            try:
                y = float(r.value_str)
            except Exception:
                continue
            x = (r.time_us - t0) / 1_000_000.0
            series_map[r.function].x.append(x)
            series_map[r.function].y.append(y)

    return [s for s in series_map.values()]


def render_plot(fig: Figure, series: List[PlotSeries]) -> None:
    fig.clear()
    ax = fig.add_subplot(111)

    if not series:
        ax.set_title('No data')
        ax.set_xlabel('Time (s)')
        return

    ax.set_xlabel('Time (s)')
    for s in series:
        ax.plot(s.x, s.y, label=f"{s.name} ({s.unit})")

    ax.legend(loc='best')
    ax.grid(True)

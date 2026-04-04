from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

from matplotlib.figure import Figure

from .utils import ParsedRecord


@dataclass
class PlotSeries:
    name: str
    unit: str
    x: List[float]
    y: List[float]


def build_series(records: List[ParsedRecord], targets: Dict[str, Tuple[str, str]], x_range: Optional[Tuple[float, float]] = None) -> List[PlotSeries]:
    """Build plot series.

    Args:
        records: parsed records
        targets: mapping from function name to (series name, unit)
        x_range: optional (xmin, xmax) in seconds (relative to first valid record)

    English note:
        x_range is applied after converting timestamps to relative seconds.
    """
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
            if x_range is not None:
                xmin, xmax = x_range
                if x < xmin or x > xmax:
                    continue
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

    # Legend outside (right side) to avoid covering the plot
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
    ax.grid(True)

    # Reserve space for legend
    try:
        fig.tight_layout(rect=(0, 0, 0.82, 1))
    except Exception:
        pass

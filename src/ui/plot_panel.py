from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from ..models.record import ParsedRecord
from ..services.plotter import build_series, render_plot

# Maps the checkbox label (== ParsedRecord.function) to (series name, unit).
_PLOT_TARGETS: Dict[str, Tuple[str, str]] = {
    'Voltage()': ('Voltage', 'mV'),
    'Current()': ('Current', 'mA'),
    'RelativeStateOfCharge()': ('RSOC', '%'),
}


class PlotPanel(ttk.LabelFrame):
    """Matplotlib time-series panel with per-series toggles and an x-range."""

    def __init__(self, master: tk.Misc, *, on_refresh: Callable[[], None]):
        super().__init__(master, text='Plot')

        controls = ttk.Frame(self)
        controls.pack(fill='x', padx=8, pady=(8, 4))

        self.plot_vars: Dict[str, tk.BooleanVar] = {}
        for label in _PLOT_TARGETS:
            var = tk.BooleanVar(value=True)
            self.plot_vars[label] = var
            ttk.Checkbutton(controls, text=label, variable=var, command=on_refresh).pack(side='left', padx=6)

        ttk.Label(controls, text='Plot Range (s):').pack(side='left', padx=(14, 4))
        self.xmin_var = tk.StringVar(value='')
        self.xmax_var = tk.StringVar(value='')
        ttk.Entry(controls, textvariable=self.xmin_var, width=8).pack(side='left')
        ttk.Label(controls, text='~').pack(side='left', padx=4)
        ttk.Entry(controls, textvariable=self.xmax_var, width=8).pack(side='left')

        ttk.Button(controls, text='Refresh Plot', command=on_refresh).pack(side='right')

        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)

        render_plot(self.fig, [])
        self.canvas.draw()

    def _selected_targets(self) -> Dict[str, Tuple[str, str]]:
        return {label: spec for label, spec in _PLOT_TARGETS.items() if self.plot_vars[label].get()}

    def _x_range(self) -> Optional[Tuple[float, float]]:
        try:
            xmin_txt = self.xmin_var.get().strip()
            xmax_txt = self.xmax_var.get().strip()
            if xmin_txt == '' and xmax_txt == '':
                return None
            xmin = float(xmin_txt) if xmin_txt != '' else float('-inf')
            xmax = float(xmax_txt) if xmax_txt != '' else float('inf')
            return (xmin, xmax)
        except ValueError:
            return None

    def refresh(self, records: List[ParsedRecord]) -> None:
        if not records:
            render_plot(self.fig, [])
            self.canvas.draw()
            return
        series = build_series(records, self._selected_targets(), x_range=self._x_range())
        render_plot(self.fig, series)
        self.canvas.draw()

    def save_photo(self, path: str) -> None:
        self.fig.savefig(path, dpi=200, bbox_inches='tight')

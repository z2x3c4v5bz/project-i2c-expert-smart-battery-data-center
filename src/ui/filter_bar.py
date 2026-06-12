from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Tuple


class FilterBar(ttk.LabelFrame):
    """The 'Filters' bar: device/command entries, hide-invalid, time format.

    Owns its widgets and exposes plain getters; it does not touch app state.
    The controller passes callbacks and reads ``get_inputs()`` on demand.
    """

    def __init__(self, master: tk.Misc, *, on_apply: Callable[[], None],
                 on_clear: Callable[[], None], on_time_format_change: Callable[[], None]):
        super().__init__(master, text='Filters')

        ttk.Label(self, text='Device Address (hex):').pack(side='left', padx=(10, 4))
        self.dev_entry = ttk.Entry(self, width=10)
        self.dev_entry.pack(side='left', padx=4)

        ttk.Label(self, text='Command Code (hex):').pack(side='left', padx=(14, 4))
        self.cmd_entry = ttk.Entry(self, width=12)
        self.cmd_entry.pack(side='left', padx=4)

        self.hide_invalid_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text='Hide Invalid', variable=self.hide_invalid_var,
                        command=on_apply).pack(side='left', padx=(14, 4))

        ttk.Label(self, text='Log Time Format:').pack(side='left', padx=(14, 4))
        self.time_format_var = tk.StringVar(value='legacy')
        self.time_format_cb = ttk.Combobox(self, textvariable=self.time_format_var,
                                            state='readonly', width=10)
        self.time_format_cb['values'] = ['legacy', 'new']
        self.time_format_cb.pack(side='left', padx=4)
        self.time_format_cb.bind('<<ComboboxSelected>>', lambda e: on_time_format_change())

        ttk.Button(self, text='Apply', command=on_apply).pack(side='left', padx=6)
        ttk.Button(self, text='Clear', command=on_clear).pack(side='left', padx=6)

    def get_inputs(self) -> Tuple[str, str, bool]:
        """Return (device_hex, command_hex, hide_invalid) as typed by the user."""
        return (
            self.dev_entry.get().strip(),
            self.cmd_entry.get().strip(),
            bool(self.hide_invalid_var.get()),
        )

    @property
    def time_format(self) -> str:
        return self.time_format_var.get()

    def clear_inputs(self) -> None:
        self.hide_invalid_var.set(False)
        self.dev_entry.delete(0, 'end')
        self.cmd_entry.delete(0, 'end')

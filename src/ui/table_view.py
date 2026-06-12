from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, List

from ..models.record import ParsedRecord
from ..utils import canonical_hex, format_time_us_to_hhmmssus


class RecordTableView(ttk.Frame):
    """The main records Treeview plus its scrollbars.

    Row iids are the view-row index as a string (``"0"``, ``"1"`` ...), matching
    positions into ``visible_indices``. All cell formatting lives here so the
    controller never builds display strings.
    """

    COLS = ('Index', 'Time', 'RW', 'ACK/NACK', 'Device Address',
            'Command Code', 'Function', 'Value', 'Unit', 'Data')

    def __init__(self, master: tk.Misc, *, on_select: Callable[[], None]):
        super().__init__(master)

        self.tree = ttk.Treeview(self, columns=self.COLS, show='headings', height=18)
        for c in self.COLS:
            self.tree.heading(c, text=c)
            if c == 'Data':
                self.tree.column(c, width=560, anchor='w')
            elif c == 'Function':
                self.tree.column(c, width=240, anchor='w')
            elif c == 'Command Code':
                self.tree.column(c, width=120, anchor='w')
            elif c == 'ACK/NACK':
                self.tree.column(c, width=90, anchor='center')
            elif c == 'Time':
                self.tree.column(c, width=140, anchor='w')
            elif c == 'Index':
                self.tree.column(c, width=70, anchor='e')
            else:
                self.tree.column(c, width=110, anchor='w')

        self.tree.grid(row=0, column=0, sticky='nsew')

        ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.grid(row=0, column=1, sticky='ns')

        xsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(xscroll=xsb.set)
        xsb.grid(row=1, column=0, sticky='ew')

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.tree.bind('<<TreeviewSelect>>', lambda _e: on_select())

    def populate(self, records: List[ParsedRecord], visible_indices: List[int]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        if not records:
            return

        for view_row, idx in enumerate(visible_indices):
            r = records[idx]
            time_str = format_time_us_to_hhmmssus(r.time_us) if (r.time_us is not None) else ''
            ack_str = 'NA' if (r.is_valid and r.is_nack) else ('A' if r.is_valid else '')

            cmd_str = ''
            if r.is_valid:
                try:
                    cmd_str = canonical_hex(r.command_code)
                except ValueError:
                    cmd_str = r.command_code

            self.tree.insert('', 'end', iid=str(view_row), values=(
                str(idx),
                time_str,
                r.rw if r.is_valid else '',
                ack_str,
                r.device_address if r.is_valid else '',
                cmd_str,
                r.function if r.is_valid else '',
                r.value_str if r.is_valid else '',
                r.unit if r.is_valid else '',
                r.data_raw,
            ))

    def has_selection(self) -> bool:
        return bool(self.tree.selection())

    def current_view_row(self) -> int:
        sel = self.tree.selection()
        if not sel:
            return -1
        try:
            return int(sel[0])
        except (ValueError, IndexError):
            return -1

    def select_view_row(self, pos: int) -> None:
        iid = str(pos)
        self.tree.selection_set(iid)
        self.tree.see(iid)

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..models.record import ParsedRecord
from ..models.sbs import SbsConfig
from ..utils import canonical_hex

_CELL_W = 14


class BitFieldView(ttk.LabelFrame):
    """Scrollable panel showing the selected record's bytes as a bit grid."""

    def __init__(self, master: tk.Misc):
        super().__init__(master, text='Bit Field')

        self.canvas = tk.Canvas(self, highlightthickness=0)
        ysb = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        xsb = ttk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        ysb.grid(row=0, column=1, sticky='ns')
        xsb.grid(row=1, column=0, sticky='ew')

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.container = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.container, anchor='nw')
        self.container.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

    def render(self, rec: Optional[ParsedRecord], cfg: Optional[SbsConfig]) -> None:
        for w in self.container.winfo_children():
            w.destroy()

        if rec is None or cfg is None:
            ttk.Label(self.container, text='(No selection)').pack(anchor='w')
            return
        if not rec.is_valid:
            ttk.Label(self.container, text='(Invalid record)').pack(anchor='w')
            return

        try:
            cc_norm = canonical_hex(rec.command_code)
        except ValueError:
            cc_norm = ''
        if not cc_norm or cc_norm not in cfg.body:
            ttk.Label(self.container, text='(No bit-field definition)').pack(anchor='w')
            return

        d = cfg.body[cc_norm]
        if d.is_value or not d.bitfield:
            ttk.Label(self.container, text='(No bit-field definition)').pack(anchor='w')
            return

        n = len(rec.bytes_le)
        if n <= 0:
            ttk.Label(self.container, text='(No byte data)').pack(anchor='w')
            return

        # Display high byte first (byte index is list index because bytes_le is low->high).
        for bi in range(n - 1, -1, -1):
            b = rec.bytes_le[bi]
            frame = ttk.LabelFrame(self.container, text=f'Byte {bi}')
            frame.pack(fill='x', pady=6)

            for col in range(8):
                frame.columnconfigure(col, weight=0)

            for col, bit in enumerate(range(7, -1, -1)):
                idx = bi * 8 + bit
                title = d.bitfield.get(str(idx), f'bit{idx}')
                ttk.Label(frame, text=title, width=_CELL_W, anchor='center',
                          borderwidth=1, relief='solid').grid(row=0, column=col, sticky='nsew', padx=1, pady=1)

            for col, bit in enumerate(range(7, -1, -1)):
                val = (b >> bit) & 1
                ttk.Label(frame, text=str(val), width=_CELL_W, anchor='center',
                          borderwidth=1, relief='solid').grid(row=1, column=col, sticky='nsew', padx=1, pady=1)

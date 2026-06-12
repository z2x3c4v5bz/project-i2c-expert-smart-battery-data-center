from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class ProgressDialog(tk.Toplevel):
    """Modal indeterminate progress bar for background operations."""

    def __init__(self, master: tk.Misc, text: str = 'Processing...'):
        super().__init__(master)
        self.title('Progress')
        self.geometry('460x140')
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', lambda: None)

        ttk.Label(self, text=text).pack(pady=(22, 10))
        self.pb = ttk.Progressbar(self, mode='indeterminate')
        self.pb.pack(fill='x', padx=20, pady=10)
        self.pb.start(12)

        self.transient(master)
        self.grab_set()

    def close(self):
        self.pb.stop()
        self.grab_release()
        self.destroy()


class SearchDialog(tk.Toplevel):
    """Search dialog with Find Previous / Find Next.

    Decoupled from ``App``: it only knows a title, a prompt and an ``on_find``
    callback invoked as ``on_find(direction, query)`` where direction is -1/+1.
    """

    def __init__(self, master: tk.Misc, title: str, prompt: str, initial: str,
                 on_find: Callable[[int, str], None]):
        super().__init__(master)
        self._on_find = on_find

        self.title(title)
        self.geometry('340x135')
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        try:
            pw = master.winfo_width(); ph = master.winfo_height()
            px = master.winfo_rootx(); py = master.winfo_rooty()
            w = self.winfo_width(); h = self.winfo_height()
            x = px + int((pw - w) / 2)
            y = py + int((ph - h) / 2)
            self.geometry(f'{w}x{h}+{x}+{y}')
        except Exception:
            pass

        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=12, pady=12)

        ttk.Label(frm, text=prompt).grid(row=0, column=0, sticky='w')
        self.var = tk.StringVar(value=initial)
        ent = ttk.Entry(frm, textvariable=self.var, width=28)
        ent.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(6, 8))

        ttk.Button(frm, text='Find Previous', command=lambda: self._do_find(-1)).grid(row=2, column=0, sticky='w', padx=(0, 8))
        ttk.Button(frm, text='Find Next', command=lambda: self._do_find(+1)).grid(row=2, column=1, sticky='w')

        frm.columnconfigure(1, weight=1)

        self.transient(master)
        self.grab_set()
        ent.focus_set()

    def _do_find(self, direction: int):
        q = self.var.get().strip()
        if not q:
            return
        self._on_find(direction, q)

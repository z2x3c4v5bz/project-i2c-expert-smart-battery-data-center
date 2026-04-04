from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict

from .sbs_config import SbsConfig, SbsCommandDef, save_config, FUNCTION_TYPE, ACCESS_TYPE


class ConfigEditor(tk.Toplevel):
    """Modal config editor window.

    Design notes:
    - FunctionType != 0 => Function is auto-filled and read-only.
    - Access and FunctionType are displayed as text in UI but stored as numeric in JSON.
    """

    def __init__(self, master: tk.Misc, cfg: SbsConfig):
        super().__init__(master)
        self.title('SBS Config Editor')
        self.geometry('980x650')
        self.resizable(True, True)

        self.cfg = cfg
        self._filtered_keys = list(cfg.body.keys())

        self.protocol('WM_DELETE_WINDOW', self._on_close)

        # UI
        top = ttk.Frame(self)
        top.pack(fill='x', padx=10, pady=8)

        ttk.Label(top, text='Title:').pack(side='left')
        self.title_var = tk.StringVar(value=self.cfg.title)
        ttk.Entry(top, textvariable=self.title_var, width=50).pack(side='left', padx=(5, 20))

        ttk.Label(top, text='Search Command:').pack(side='left')
        self.search_var = tk.StringVar(value='')
        ent = ttk.Entry(top, textvariable=self.search_var, width=20)
        ent.pack(side='left', padx=5)
        ent.bind('<KeyRelease>', lambda e: self._apply_filter())

        btns = ttk.Frame(top)
        btns.pack(side='right')
        ttk.Button(btns, text='Save As...', command=self._save_as).pack(side='left', padx=4)
        ttk.Button(btns, text='Close', command=self._on_close).pack(side='left', padx=4)

        main = ttk.Frame(self)
        main.pack(fill='both', expand=True, padx=10, pady=10)

        # Treeview
        cols = ('Command', 'Function', 'FunctionType', 'Access', 'IsValue', 'Unit')
        self.tree = ttk.Treeview(main, columns=cols, show='headings', height=20)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140 if c != 'Function' else 280, anchor='w')
        self.tree.pack(side='left', fill='both', expand=True)

        ysb = ttk.Scrollbar(main, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.pack(side='left', fill='y')

        # Detail editor
        detail = ttk.LabelFrame(main, text='Detail')
        detail.pack(side='left', fill='y', padx=(10, 0))

        self.cmd_var = tk.StringVar(value='')
        self.fn_var = tk.StringVar(value='')
        self.ft_var = tk.IntVar(value=0)
        self.acc_var = tk.IntVar(value=0)
        self.isv_var = tk.BooleanVar(value=False)
        self.unit_var = tk.StringVar(value='NA')

        # widgets
        row = 0
        ttk.Label(detail, text='Command Code').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        ttk.Entry(detail, textvariable=self.cmd_var, state='readonly', width=18).grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='FunctionType').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        self.ft_cb = ttk.Combobox(detail, state='readonly', width=22)
        self.ft_cb['values'] = [f"{k}: {v}" for k, v in FUNCTION_TYPE.items()]
        self.ft_cb.grid(row=row, column=1, sticky='w', padx=6, pady=4)
        self.ft_cb.bind('<<ComboboxSelected>>', lambda e: self._on_ft_change())

        row += 1
        ttk.Label(detail, text='Function').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        self.fn_ent = ttk.Entry(detail, textvariable=self.fn_var, width=26)
        self.fn_ent.grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='Access').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        self.acc_cb = ttk.Combobox(detail, state='readonly', width=22)
        self.acc_cb['values'] = [f"{k}: {v}" for k, v in ACCESS_TYPE.items()]
        self.acc_cb.grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='IsValue').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        ttk.Checkbutton(detail, variable=self.isv_var, command=self._on_isv_change).grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='Unit').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        ttk.Entry(detail, textvariable=self.unit_var, width=26).grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='BitField (JSON)').grid(row=row, column=0, sticky='nw', padx=6, pady=4)
        self.bit_txt = tk.Text(detail, width=28, height=18)
        self.bit_txt.grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Button(detail, text='Apply Changes', command=self._apply_changes).grid(row=row, column=0, columnspan=2, pady=(10, 4))

        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        self._populate_tree()

        # make modal
        self.transient(master)
        self.grab_set()
        self.focus_set()

    def _populate_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for cc in self._filtered_keys:
            d = self.cfg.body[cc]
            self.tree.insert('', 'end', iid=cc, values=(
                cc,
                d.function,
                f"{d.function_type}: {FUNCTION_TYPE.get(d.function_type, 'Unknown')}",
                f"{d.access}: {ACCESS_TYPE.get(d.access, 'NA')}",
                str(d.is_value),
                d.unit,
            ))

    def _apply_filter(self):
        q = self.search_var.get().strip().upper()
        if not q:
            self._filtered_keys = list(self.cfg.body.keys())
        else:
            self._filtered_keys = [k for k in self.cfg.body.keys() if q in k]
        self._populate_tree()

    def _on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        cc = sel[0]
        d = self.cfg.body[cc]
        self.cmd_var.set(cc)
        self.fn_var.set(d.function)
        # set combobox indexes
        self.ft_cb.current(d.function_type if d.function_type in FUNCTION_TYPE else 0)
        self.acc_cb.current(d.access if d.access in ACCESS_TYPE else 0)
        self.isv_var.set(d.is_value)
        self.unit_var.set(d.unit)
        self.bit_txt.delete('1.0', 'end')
        try:
            import json
            self.bit_txt.insert('1.0', json.dumps(d.bitfield, indent=2))
        except Exception:
            self.bit_txt.insert('1.0', '{}')
        self._sync_function_editable()

    def _on_ft_change(self):
        idx = self.ft_cb.current()
        # idx is aligned with keys order (0..)
        ft = idx
        self.ft_var.set(ft)
        if ft != 0:
            self.fn_var.set(FUNCTION_TYPE.get(ft, self.fn_var.get()))
        self._sync_function_editable()

    def _sync_function_editable(self):
        ft = self.ft_cb.current()
        if ft != 0:
            self.fn_ent.config(state='readonly')
        else:
            self.fn_ent.config(state='normal')

    def _on_isv_change(self):
        if self.isv_var.get():
            # IsValue=true => unit default NA and BitField empty (per draft)
            if not self.unit_var.get().strip():
                self.unit_var.set('NA')

    def _apply_changes(self):
        cc = self.cmd_var.get().strip().upper()
        if not cc:
            return
        d = self.cfg.body[cc]
        ft = self.ft_cb.current()
        acc = self.acc_cb.current()
        fn = self.fn_var.get().strip()
        if ft != 0:
            fn = FUNCTION_TYPE.get(ft, fn)

        # Parse bitfield JSON
        bitfield = {}
        import json
        try:
            bitfield = json.loads(self.bit_txt.get('1.0', 'end').strip() or '{}')
            if not isinstance(bitfield, dict):
                raise ValueError('BitField must be a JSON object')
        except Exception as e:
            messagebox.showerror('BitField Error', f'Invalid BitField JSON: {e}', parent=self)
            return

        isv = bool(self.isv_var.get())
        unit = self.unit_var.get().strip() or 'NA'
        if isv:
            bitfield = {}  # enforce
            if not unit:
                unit = 'NA'

        self.cfg.body[cc] = SbsCommandDef(
            function=fn,
            function_type=ft,
            access=acc,
            is_value=isv,
            unit=unit,
            bitfield=bitfield,
        )

        self.cfg.title = self.title_var.get().strip() or self.cfg.title

        # refresh row
        self._populate_tree()
        messagebox.showinfo('Applied', f'Updated {cc}', parent=self)

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension='.json',
            filetypes=[('JSON', '*.json')],
            title='Save SBS Config As'
        )
        if not path:
            return
        try:
            save_config(self.cfg, path)
            messagebox.showinfo('Saved', f'Saved to: {path}', parent=self)
        except Exception as e:
            messagebox.showerror('Save Error', str(e), parent=self)

    def _on_close(self):
        self.grab_release()
        self.destroy()

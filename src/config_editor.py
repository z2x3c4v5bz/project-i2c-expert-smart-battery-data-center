from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Optional, Tuple

from .sbs_config import SbsConfig, SbsCommandDef, save_config, FUNCTION_TYPE, ACCESS_TYPE


def _validate_unique_functions(cfg: SbsConfig) -> Tuple[bool, str]:
    """Validate uniqueness of FunctionType and Function (except Customize)."""
    seen_ft: Dict[int, str] = {}
    seen_fn: Dict[str, str] = {}

    for cc, d in cfg.body.items():
        ft = int(d.function_type)
        fn = str(d.function)
        if ft == 0:
            continue

        if ft in seen_ft:
            return False, f"Duplicate FunctionType detected: {ft} ({FUNCTION_TYPE.get(ft,'Unknown')})\n- {seen_ft[ft]}\n- {cc}"
        seen_ft[ft] = cc

        if fn in seen_fn:
            return False, f"Duplicate Function detected: {fn}\n- {seen_fn[fn]}\n- {cc}"
        seen_fn[fn] = cc

    return True, 'OK'


class BitFieldEditor(tk.Toplevel):
    """Bit field editor for a single Command Code (dynamic bit index)."""

    def __init__(self, master: tk.Misc, bitfield: Dict[str, str], cc: str):
        super().__init__(master)
        self.title(f'Edit Bit Field - {cc}')
        self.geometry('740x520')
        self.minsize(660, 460)
        self.resizable(True, True)

        self.bitfield = bitfield  # reference

        cols = ('Bit', 'Function')
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=16)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120 if c == 'Bit' else 540, anchor='w')
        self.tree.grid(row=0, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)

        ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.grid(row=0, column=3, sticky='ns', pady=10)

        xsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(xscroll=xsb.set)
        xsb.grid(row=1, column=0, columnspan=3, sticky='ew', padx=10)

        btn_row = ttk.Frame(self)
        btn_row.grid(row=2, column=0, columnspan=4, sticky='ew', padx=10, pady=(8, 6))

        ttk.Label(btn_row, text='Bit Index:').pack(side='left')
        self.bit_var = tk.StringVar(value='')
        ttk.Entry(btn_row, textvariable=self.bit_var, width=10).pack(side='left', padx=6)

        ttk.Label(btn_row, text='Function:').pack(side='left')
        self.fn_var = tk.StringVar(value='')
        ttk.Entry(btn_row, textvariable=self.fn_var, width=44).pack(side='left', padx=6)

        ttk.Button(btn_row, text='Add / Update', command=self.on_add).pack(side='left', padx=6)
        ttk.Button(btn_row, text='Delete Selected', command=self.on_delete).pack(side='left', padx=6)

        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, columnspan=4, sticky='ew', padx=10, pady=(0, 10))
        ttk.Button(bottom, text='Close', command=self.on_close).pack(side='right')

        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self._populate()

        self.transient(master)
        self.grab_set()
        self.focus_set()

    def _populate(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        def sort_key(k: str) -> int:
            try:
                return int(k)
            except Exception:
                return 10**9

        for bit in sorted(self.bitfield.keys(), key=sort_key):
            self.tree.insert('', 'end', iid=str(bit), values=(str(bit), self.bitfield[bit]))

    def on_add(self):
        bit_txt = self.bit_var.get().strip()
        fn_txt = self.fn_var.get().strip()

        if not bit_txt:
            messagebox.showwarning('Input', 'Bit Index is required.', parent=self)
            return
        if not fn_txt:
            messagebox.showwarning('Input', 'Function name is required.', parent=self)
            return

        try:
            bit_int = int(bit_txt)
        except Exception:
            messagebox.showerror('Input', 'Bit Index must be an integer (>= 0).', parent=self)
            return

        if bit_int < 0 or bit_int > 1023:
            messagebox.showerror('Input', 'Bit Index out of range. Allowed: 0~1023.', parent=self)
            return

        self.bitfield[str(bit_int)] = fn_txt
        self._populate()

    def on_delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        bit = sel[0]
        if bit in self.bitfield:
            del self.bitfield[bit]
        self._populate()

    def on_close(self):
        self.grab_release()
        self.destroy()


class ConfigEditor(tk.Toplevel):
    """Modal SBS config editor window."""

    def __init__(self, master: tk.Misc, cfg: SbsConfig):
        super().__init__(master)
        self.title('SBS Config Editor')
        self.geometry('1240x760')
        self.minsize(1140, 700)
        self.resizable(True, True)

        self.cfg = cfg
        self._filtered_keys = list(cfg.body.keys())
        self._current_cc: Optional[str] = None

        self.protocol('WM_DELETE_WINDOW', self._on_close)

        top = ttk.Frame(self)
        top.pack(fill='x', padx=10, pady=8)

        ttk.Label(top, text='Title:').pack(side='left')
        self.title_var = tk.StringVar(value=self.cfg.title)
        ttk.Entry(top, textvariable=self.title_var, width=54).pack(side='left', padx=(5, 16))

        ttk.Label(top, text='Search:').pack(side='left')
        self.search_var = tk.StringVar(value='')
        ent = ttk.Entry(top, textvariable=self.search_var, width=22)
        ent.pack(side='left', padx=5)
        ent.bind('<KeyRelease>', lambda e: self._apply_filter())

        ttk.Label(top, text='Go to Command:').pack(side='left', padx=(12, 0))
        self.goto_var = tk.StringVar(value='')
        ttk.Entry(top, textvariable=self.goto_var, width=10).pack(side='left', padx=5)
        ttk.Button(top, text='Go', command=self._go_to_command).pack(side='left')

        btns = ttk.Frame(top)
        btns.pack(side='right')
        ttk.Button(btns, text='Save', command=self._save).pack(side='left', padx=4)
        ttk.Button(btns, text='Save As...', command=self._save_as).pack(side='left', padx=4)
        ttk.Button(btns, text='Close', command=self._on_close).pack(side='left', padx=4)

        main = ttk.Frame(self)
        main.pack(fill='both', expand=True, padx=10, pady=10)

        cols = ('Command', 'Function', 'FunctionType', 'Access', 'IsValue', 'Unit')
        self.tree = ttk.Treeview(main, columns=cols, show='headings', height=24)
        for c in cols:
            self.tree.heading(c, text=c)
            if c == 'Function':
                self.tree.column(c, width=360, anchor='w')
            elif c == 'Unit':
                self.tree.column(c, width=140, anchor='w')
            else:
                self.tree.column(c, width=150, anchor='w')
        self.tree.pack(side='left', fill='both', expand=True)

        ysb = ttk.Scrollbar(main, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.pack(side='left', fill='y')

        xsb = ttk.Scrollbar(main, orient='horizontal', command=self.tree.xview)
        self.tree.configure(xscroll=xsb.set)
        xsb.pack(side='bottom', fill='x')

        detail = ttk.LabelFrame(main, text='Selected Command Detail')
        detail.pack(side='left', fill='y', padx=(12, 0))

        self.cmd_var = tk.StringVar(value='')
        self.fn_var = tk.StringVar(value='')
        self.isv_var = tk.BooleanVar(value=False)
        self.unit_var = tk.StringVar(value='NA')

        row = 0
        ttk.Label(detail, text='Command Code').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        ttk.Entry(detail, textvariable=self.cmd_var, state='readonly', width=22).grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='FunctionType').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        self.ft_cb = ttk.Combobox(detail, state='readonly', width=30)
        self.ft_cb['values'] = [f"{k}: {v}" for k, v in FUNCTION_TYPE.items()]
        self.ft_cb.grid(row=row, column=1, sticky='w', padx=6, pady=4)
        self.ft_cb.bind('<<ComboboxSelected>>', lambda e: self._on_ft_change())

        row += 1
        ttk.Label(detail, text='Function').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        self.fn_ent = ttk.Entry(detail, textvariable=self.fn_var, width=34)
        self.fn_ent.grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='Access').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        self.acc_cb = ttk.Combobox(detail, state='readonly', width=30)
        self.acc_cb['values'] = [f"{k}: {v}" for k, v in ACCESS_TYPE.items()]
        self.acc_cb.grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='IsValue').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        ttk.Checkbutton(detail, variable=self.isv_var, command=self._on_isv_change).grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='Unit').grid(row=row, column=0, sticky='w', padx=6, pady=4)
        ttk.Entry(detail, textvariable=self.unit_var, width=34).grid(row=row, column=1, sticky='w', padx=6, pady=4)

        row += 1
        ttk.Label(detail, text='BitField').grid(row=row, column=0, sticky='w', padx=6, pady=(10, 4))
        self.bf_summary = tk.StringVar(value='{}')
        ttk.Label(detail, textvariable=self.bf_summary, width=38, foreground='#374151').grid(row=row, column=1, sticky='w', padx=6, pady=(10, 4))

        row += 1
        self.bf_btn = ttk.Button(detail, text='Edit Bit Field...', command=self._edit_bitfield)
        self.bf_btn.grid(row=row, column=0, columnspan=2, pady=(0, 10))

        row += 1
        ttk.Button(detail, text='Apply Changes', command=self._apply_changes).grid(row=row, column=0, columnspan=2, pady=(6, 10))

        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        self._populate_tree()

        self.transient(master)
        self.grab_set()
        self.focus_set()

    def _populate_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for cc in self._filtered_keys:
            self._insert_or_update_row(cc)

    def _insert_or_update_row(self, cc: str):
        d = self.cfg.body[cc]
        values = (
            cc,
            d.function,
            f"{d.function_type}: {FUNCTION_TYPE.get(d.function_type, 'Unknown')}",
            f"{d.access}: {ACCESS_TYPE.get(d.access, 'NA')}",
            str(d.is_value),
            d.unit,
        )
        if self.tree.exists(cc):
            self.tree.item(cc, values=values)
        else:
            self.tree.insert('', 'end', iid=cc, values=values)

    def _apply_filter(self):
        q = self.search_var.get().strip().lower()
        if not q:
            self._filtered_keys = list(self.cfg.body.keys())
        else:
            self._filtered_keys = [k for k, d in self.cfg.body.items() if q in k.lower() or q in (d.function or '').lower()]
        self._populate_tree()

    def _go_to_command(self):
        cc = self.goto_var.get().strip()
        if not cc:
            return
        try:
            cc_norm = f"0x{int(cc, 16):02X}" if not cc.lower().startswith('0x') else f"0x{int(cc, 16):02X}"
        except Exception:
            messagebox.showerror('Go', 'Invalid command code. Use hex like 2D or 0x2D.', parent=self)
            return

        if cc_norm not in self.cfg.body:
            messagebox.showwarning('Go', f'Command not found: {cc_norm}', parent=self)
            return

        self.search_var.set('')
        self._filtered_keys = list(self.cfg.body.keys())
        self._populate_tree()

        self.tree.selection_set(cc_norm)
        self.tree.see(cc_norm)
        self._on_select()

    def _on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            self._current_cc = None
            return
        cc = sel[0]
        d = self.cfg.body[cc]

        self._current_cc = cc
        self.cmd_var.set(cc)
        self.fn_var.set(d.function)
        self.ft_cb.current(d.function_type if d.function_type in FUNCTION_TYPE else 0)
        self.acc_cb.current(d.access if d.access in ACCESS_TYPE else 0)
        self.isv_var.set(d.is_value)
        self.unit_var.set(d.unit)

        self._refresh_bitfield_summary()
        self._sync_function_editable()
        self._sync_bitfield_button()

    def _refresh_bitfield_summary(self):
        if self._current_cc is None:
            self.bf_summary.set('{}')
            return
        d = self.cfg.body[self._current_cc]
        if not d.bitfield:
            self.bf_summary.set('{}')
        else:
            items = sorted(d.bitfield.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 10**9)
            preview = ', '.join([f"{k}:{v}" for k, v in items[:6]])
            if len(items) > 6:
                preview += ', ...'
            self.bf_summary.set('{' + preview + '}')

    def _on_ft_change(self):
        ft = self.ft_cb.current()
        if ft != 0:
            self.fn_var.set(FUNCTION_TYPE.get(ft, self.fn_var.get()))
        self._sync_function_editable()

    def _sync_function_editable(self):
        ft = self.ft_cb.current()
        self.fn_ent.config(state='readonly' if ft != 0 else 'normal')

    def _on_isv_change(self):
        self._sync_bitfield_button()

    def _sync_bitfield_button(self):
        if self._current_cc is None:
            self.bf_btn.config(state='disabled')
            return
        self.bf_btn.config(state='disabled' if self.isv_var.get() else 'normal')

    def _edit_bitfield(self):
        if self._current_cc is None:
            return
        if self.isv_var.get():
            return
        d = self.cfg.body[self._current_cc]
        if d.bitfield is None:
            d.bitfield = {}
        editor = BitFieldEditor(self, d.bitfield, self._current_cc)
        self.wait_window(editor)
        self._refresh_bitfield_summary()

    def _apply_changes(self):
        if self._current_cc is None:
            messagebox.showwarning('Apply', 'Please select a Command Code first.', parent=self)
            return

        cc = self._current_cc
        d = self.cfg.body[cc]

        ft = self.ft_cb.current()
        acc = self.acc_cb.current()
        fn = self.fn_var.get().strip()
        isv = bool(self.isv_var.get())
        unit = self.unit_var.get().strip() or 'NA'

        if ft != 0:
            fn = FUNCTION_TYPE.get(ft, fn)

        bitfield = d.bitfield if isinstance(d.bitfield, dict) else {}
        if isv:
            bitfield = {}

        self.cfg.body[cc] = SbsCommandDef(
            function=fn,
            function_type=ft,
            access=acc,
            is_value=isv,
            unit=unit,
            bitfield=bitfield,
        )

        self.cfg.title = self.title_var.get().strip() or self.cfg.title

        self._insert_or_update_row(cc)
        self.tree.selection_set(cc)
        self._refresh_bitfield_summary()

        messagebox.showinfo('Applied', f'Updated {cc}', parent=self)

    def _save(self):
        if not messagebox.askyesno('Save', 'Do you want to save changes to the original file?', parent=self):
            return

        ok, msg = _validate_unique_functions(self.cfg)
        if not ok:
            messagebox.showerror('Save', msg, parent=self)
            return

        if self.cfg.path is None:
            self._save_as()
            return

        try:
            save_config(self.cfg, self.cfg.path)
            messagebox.showinfo('Saved', f'Saved to: {self.cfg.path}', parent=self)
        except Exception as e:
            messagebox.showerror('Save Error', str(e), parent=self)

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension='.json',
            filetypes=[('JSON', '*.json')],
            title='Save SBS Config As'
        )
        if not path:
            return

        if not messagebox.askyesno('Save As', 'Do you want to save changes to this file?', parent=self):
            return

        ok, msg = _validate_unique_functions(self.cfg)
        if not ok:
            messagebox.showerror('Save As', msg, parent=self)
            return

        try:
            save_config(self.cfg, path)
            messagebox.showinfo('Saved', f'Saved to: {path}', parent=self)
            from pathlib import Path
            self.cfg.path = Path(path)
        except Exception as e:
            messagebox.showerror('Save Error', str(e), parent=self)

    def _on_close(self):
        self.grab_release()
        self.destroy()

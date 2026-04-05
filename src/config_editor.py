from __future__ import annotations

import copy
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
    def __init__(self, master: tk.Misc, initial: Dict[str, str], cc: str):
        super().__init__(master)
        self.title(f'Edit Bit Field - {cc}')
        self.geometry('740x520')
        self.minsize(660, 460)
        self.resizable(True, True)

        self._work = copy.deepcopy(initial) if isinstance(initial, dict) else {}
        self.result: Optional[Dict[str, str]] = None

        cols = ('Bit', 'Function')
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=16)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120 if c == 'Bit' else 540, anchor='w')
        self.tree.grid(row=0, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)

        ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.grid(row=0, column=3, sticky='ns', pady=10)

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
        ttk.Button(bottom, text='OK', command=self.on_ok).pack(side='right', padx=6)
        ttk.Button(bottom, text='Cancel', command=self.on_cancel).pack(side='right')

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

        for bit in sorted(self._work.keys(), key=sort_key):
            self.tree.insert('', 'end', iid=str(bit), values=(str(bit), self._work[bit]))

    def on_add(self):
        bit_txt = self.bit_var.get().strip()
        fn_txt = self.fn_var.get().strip()
        if not bit_txt or not fn_txt:
            messagebox.showwarning('Input', 'Bit Index and Function are required.', parent=self)
            return
        try:
            bit_int = int(bit_txt)
        except Exception:
            messagebox.showerror('Input', 'Bit Index must be integer.', parent=self)
            return
        self._work[str(bit_int)] = fn_txt
        self._populate()

    def on_delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        k = sel[0]
        if k in self._work:
            del self._work[k]
        self._populate()

    def on_ok(self):
        self.result = copy.deepcopy(self._work)
        self.grab_release()
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


class ConfigEditor(tk.Toplevel):
    def __init__(self, master: tk.Misc, cfg: SbsConfig, is_new: bool = False):
        super().__init__(master)
        self.title('SBS Config Editor')
        self.geometry('1240x760')
        self.minsize(1140, 700)
        self.resizable(True, True)

        self.is_new = is_new

        # Remove minimize & maximize buttons (Windows only)
        self.update_idletasks()
        try:
            import ctypes
            GWL_STYLE = -16
            WS_MAXIMIZEBOX = 0x00010000
            WS_MINIMIZEBOX = 0x00020000
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            style = style & (~WS_MAXIMIZEBOX) & (~WS_MINIMIZEBOX)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        except Exception:
            pass

        # Center on screen
        self.update_idletasks()
        try:
            w = self.winfo_width(); h = self.winfo_height()
            sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
            x = int((sw - w) / 2); y = int((sh - h) / 2)
            self.geometry(f'{w}x{h}+{x}+{y}')
        except Exception:
            pass

        self.cfg = cfg

        self._snap_title = copy.deepcopy(cfg.title)
        self._snap_body = copy.deepcopy(cfg.body)

        self._filtered_keys = list(cfg.body.keys())
        self._current_cc: Optional[str] = None
        self._pending_bitfield: Dict[str, Dict[str, str]] = {}
        self._dirty: bool = False

        self.protocol('WM_DELETE_WINDOW', self._on_close)

        top = ttk.Frame(self)
        top.pack(fill='x', padx=10, pady=8)

        ttk.Label(top, text='Title:').pack(side='left')
        self.title_var = tk.StringVar(value=self.cfg.title)
        title_ent = ttk.Entry(top, textvariable=self.title_var, width=54)
        title_ent.pack(side='left', padx=(5, 16))
        title_ent.bind('<KeyRelease>', lambda e: self._set_dirty(True))

        ttk.Label(top, text='Search:').pack(side='left')
        self.search_var = tk.StringVar(value='')
        ent = ttk.Entry(top, textvariable=self.search_var, width=22)
        ent.pack(side='left', padx=5)
        ent.bind('<KeyRelease>', lambda e: self._apply_filter())

        btns = ttk.Frame(top)
        btns.pack(side='right')
        if not self.is_new:
            ttk.Button(btns, text='Save', command=self._save).pack(side='left', padx=4)
        ttk.Button(btns, text='Save As...', command=self._save_as).pack(side='left', padx=4)
        ttk.Button(btns, text='Close', command=self._on_close).pack(side='left', padx=4)

        pan = ttk.PanedWindow(self, orient='horizontal')
        pan.pack(fill='both', expand=True, padx=10, pady=10)

        left = ttk.Frame(pan)
        right = ttk.Frame(pan)
        pan.add(left, weight=3)
        pan.add(right, weight=2)

        cols = ('Command', 'Function', 'FunctionType', 'Access', 'IsValue', 'Unit')
        self.tree = ttk.Treeview(left, columns=cols, show='headings', height=24)
        for c in cols:
            self.tree.heading(c, text=c)
            if c == 'Function':
                self.tree.column(c, width=360, anchor='w')
            elif c == 'Unit':
                self.tree.column(c, width=140, anchor='w')
            else:
                self.tree.column(c, width=180, anchor='w')
        self.tree.grid(row=0, column=0, sticky='nsew')

        l_ysb = ttk.Scrollbar(left, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=l_ysb.set)
        l_ysb.grid(row=0, column=1, sticky='ns')

        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        detail = ttk.LabelFrame(right, text='Selected Command Detail')
        detail.pack(fill='both', expand=True)

        self.cmd_var = tk.StringVar(value='')
        self.fn_var = tk.StringVar(value='')
        self.isv_var = tk.BooleanVar(value=False)
        self.unit_var = tk.StringVar(value='NA')

        r = 0
        ttk.Label(detail, text='Command Code').grid(row=r, column=0, sticky='w', padx=6, pady=4)
        ttk.Entry(detail, textvariable=self.cmd_var, state='readonly', width=22).grid(row=r, column=1, sticky='w', padx=6, pady=4)

        r += 1
        ttk.Label(detail, text='FunctionType').grid(row=r, column=0, sticky='w', padx=6, pady=4)
        self.ft_cb = ttk.Combobox(detail, state='readonly', width=30)
        # values sorted by numeric key, so index == function_type
        self.ft_cb['values'] = [f"{k}: {FUNCTION_TYPE[k]}" for k in sorted(FUNCTION_TYPE.keys())]
        self.ft_cb.grid(row=r, column=1, sticky='w', padx=6, pady=4)
        self.ft_cb.bind('<<ComboboxSelected>>', lambda e: self._on_ft_change())

        r += 1
        ttk.Label(detail, text='Function').grid(row=r, column=0, sticky='w', padx=6, pady=4)
        self.fn_ent = ttk.Entry(detail, textvariable=self.fn_var, width=34)
        self.fn_ent.grid(row=r, column=1, sticky='w', padx=6, pady=4)
        self.fn_ent.bind('<KeyRelease>', lambda e: self._set_dirty(True))

        r += 1
        ttk.Label(detail, text='Access').grid(row=r, column=0, sticky='w', padx=6, pady=4)
        self.acc_cb = ttk.Combobox(detail, state='readonly', width=30)
        self.acc_cb['values'] = [f"{k}: {ACCESS_TYPE[k]}" for k in sorted(ACCESS_TYPE.keys())]
        self.acc_cb.grid(row=r, column=1, sticky='w', padx=6, pady=4)
        self.acc_cb.bind('<<ComboboxSelected>>', lambda e: self._set_dirty(True))

        r += 1
        ttk.Label(detail, text='IsValue').grid(row=r, column=0, sticky='w', padx=6, pady=4)
        ttk.Checkbutton(detail, variable=self.isv_var, command=self._on_isv_change).grid(row=r, column=1, sticky='w', padx=6, pady=4)

        r += 1
        ttk.Label(detail, text='Unit').grid(row=r, column=0, sticky='w', padx=6, pady=4)
        unit_ent = ttk.Entry(detail, textvariable=self.unit_var, width=34)
        unit_ent.grid(row=r, column=1, sticky='w', padx=6, pady=4)
        unit_ent.bind('<KeyRelease>', lambda e: self._set_dirty(True))

        r += 1
        ttk.Label(detail, text='BitField (pending until Apply)').grid(row=r, column=0, sticky='w', padx=6, pady=(10, 4))
        self.bf_summary = tk.StringVar(value='{}')
        ttk.Label(detail, textvariable=self.bf_summary, width=38, foreground='#374151').grid(row=r, column=1, sticky='w', padx=6, pady=(10, 4))

        r += 1
        self.bf_btn = ttk.Button(detail, text='Edit Bit Field...', command=self._edit_bitfield)
        self.bf_btn.grid(row=r, column=0, columnspan=2, pady=(0, 10))

        r += 1
        ttk.Button(detail, text='Apply Changes', command=self._apply_changes).grid(row=r, column=0, columnspan=2, pady=(6, 10))

        detail.columnconfigure(1, weight=1)

        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self._populate_tree()

        self.grab_set()
        self.focus_set()

    def _set_dirty(self, v: bool):
        self._dirty = self._dirty or v

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

    def _confirm_discard_pending_bitfield(self) -> bool:
        if not self._current_cc:
            return True
        if self._current_cc not in self._pending_bitfield:
            return True
        discard = messagebox.askyesno(
            'Pending BitField Changes',
            'BitField changes are pending (not applied).\n\nDiscard these BitField changes and continue?',
            parent=self,
            icon='warning'
        )
        if discard:
            del self._pending_bitfield[self._current_cc]
            self._refresh_bitfield_summary()
            return True
        return False

    def _on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        new_cc = sel[0]
        if self._current_cc and new_cc != self._current_cc:
            if not self._confirm_discard_pending_bitfield():
                self.tree.selection_set(self._current_cc)
                self.tree.see(self._current_cc)
                return

        cc = new_cc
        d = self.cfg.body[cc]
        self._current_cc = cc

        self.cmd_var.set(cc)
        self.fn_var.set(d.function)

        # FunctionType combobox index == function_type
        ft = int(d.function_type)
        if ft in FUNCTION_TYPE:
            self.ft_cb.current(ft)
        else:
            self.ft_cb.current(0)

        acc = int(d.access)
        if acc in ACCESS_TYPE:
            self.acc_cb.current(list(sorted(ACCESS_TYPE.keys())).index(acc))
        else:
            self.acc_cb.current(0)

        self.isv_var.set(bool(d.is_value))
        self.unit_var.set(d.unit)

        self._refresh_bitfield_summary()
        self._sync_function_editable()
        self._sync_bitfield_button()

    def _refresh_bitfield_summary(self):
        if self._current_cc is None:
            self.bf_summary.set('{}')
            return
        bf = self._pending_bitfield.get(self._current_cc, self.cfg.body[self._current_cc].bitfield)
        if not bf:
            self.bf_summary.set('{}')
            return
        items = sorted(bf.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 10**9)
        preview = ', '.join([f"{k}:{v}" for k, v in items[:6]])
        if len(items) > 6:
            preview += ', ...'
        self.bf_summary.set('{' + preview + '}')

    def _on_ft_change(self):
        ft = self.ft_cb.current()
        if ft != 0:
            self.fn_var.set(FUNCTION_TYPE.get(ft, self.fn_var.get()))
        self._sync_function_editable()
        self._set_dirty(True)

    def _sync_function_editable(self):
        ft = self.ft_cb.current()
        self.fn_ent.config(state='readonly' if ft != 0 else 'normal')

    def _on_isv_change(self):
        self._sync_bitfield_button()
        self._set_dirty(True)

    def _sync_bitfield_button(self):
        if self._current_cc is None:
            self.bf_btn.config(state='disabled')
            return
        self.bf_btn.config(state='disabled' if self.isv_var.get() else 'normal')

    def _edit_bitfield(self):
        if self._current_cc is None or self.isv_var.get():
            return
        base_bf = self._pending_bitfield.get(self._current_cc, self.cfg.body[self._current_cc].bitfield)
        editor = BitFieldEditor(self, base_bf, self._current_cc)
        self.wait_window(editor)
        if editor.result is not None:
            self._pending_bitfield[self._current_cc] = editor.result
            self._refresh_bitfield_summary()
            self._set_dirty(True)

    def _apply_changes(self):
        if self._current_cc is None:
            messagebox.showwarning('Apply', 'Please select a Command Code first.', parent=self)
            return

        cc = self._current_cc
        d0 = self.cfg.body[cc]

        ft = self.ft_cb.current()
        fn = self.fn_var.get().strip()
        if ft != 0:
            fn = FUNCTION_TYPE.get(ft, fn)

        # Access combobox index mapping
        acc_keys = list(sorted(ACCESS_TYPE.keys()))
        acc = acc_keys[self.acc_cb.current()] if 0 <= self.acc_cb.current() < len(acc_keys) else 0

        isv = bool(self.isv_var.get())
        unit = self.unit_var.get().strip() or 'NA'

        bf = {}
        if not isv:
            bf = copy.deepcopy(self._pending_bitfield.get(cc, d0.bitfield))

        self.cfg.body[cc] = SbsCommandDef(
            function=fn,
            function_type=ft,
            access=acc,
            is_value=isv,
            unit=unit,
            bitfield=bf,
        )

        self.cfg.title = self.title_var.get().strip() or self.cfg.title

        if cc in self._pending_bitfield:
            del self._pending_bitfield[cc]

        self._insert_or_update_row(cc)
        self.tree.selection_set(cc)
        self._refresh_bitfield_summary()
        self._set_dirty(True)

        messagebox.showinfo('Applied', f'Updated {cc}. (Not saved yet)', parent=self)

    def _save(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror('Save', 'Title cannot be empty.', parent=self)
            return

        if not messagebox.askyesno('Save', 'Do you want to save changes to the original file?', parent=self):
            return

        ok, msg = _validate_unique_functions(self.cfg)
        if not ok:
            messagebox.showerror('Save', msg, parent=self)
            return

        if self.cfg.path is None:
            self._save_as()
            return

        self.cfg.title = title
        try:
            save_config(self.cfg, self.cfg.path)
            self._snap_title = copy.deepcopy(self.cfg.title)
            self._snap_body = copy.deepcopy(self.cfg.body)
            self._dirty = False
            messagebox.showinfo('Saved', f'Saved to: {self.cfg.path}', parent=self)
        except Exception as e:
            messagebox.showerror('Save Error', str(e), parent=self)

    def _save_as(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror('Save As', 'Title cannot be empty.', parent=self)
            return

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

        self.cfg.title = title
        try:
            save_config(self.cfg, path)
            from pathlib import Path
            self.cfg.path = Path(path)
            self._snap_title = copy.deepcopy(self.cfg.title)
            self._snap_body = copy.deepcopy(self.cfg.body)
            self._dirty = False
            messagebox.showinfo('Saved', f'Saved to: {path}', parent=self)
        except Exception as e:
            messagebox.showerror('Save Error', str(e), parent=self)

    def _restore_snapshot(self):
        self.cfg.title = copy.deepcopy(self._snap_title)
        self.cfg.body = copy.deepcopy(self._snap_body)

    def _on_close(self):
        if self._current_cc in self._pending_bitfield:
            if not self._confirm_discard_pending_bitfield():
                return

        has_pending_any = bool(self._pending_bitfield)
        if self._dirty or has_pending_any:
            if self.is_new:
                save_first = messagebox.askyesno(
                    'Save Required',
                    'This is a new configuration that must be saved.\n\nSave now?\n(Choose No to cancel and use Save As.)',
                    parent=self,
                    icon='warning'
                )
                if save_first:
                    self._save_as()
                    return  # Don't close if save was attempted
                else:
                    return  # Cancel close
            else:
                discard = messagebox.askyesno(
                    'Unsaved Changes',
                    'Your changes have not been saved.\n\nDiscard changes and close?\n(Choose No to cancel and use Save / Save As.)',
                    parent=self,
                    icon='warning'
                )
                if not discard:
                    return
                self._restore_snapshot()

        self.grab_release()
        self.destroy()

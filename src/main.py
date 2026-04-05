from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
from typing import Optional, List, Dict, Tuple

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .sbs_config import load_config, SbsConfig, SbsConfigError
from .log_parser import parse_log_lines
from .utils import format_time_us_to_hhmmssus, ParsedRecord
from .config_editor import ConfigEditor
from .plotter import build_series, render_plot
from .updater import check_update

APP_VERSION = '0.8.0-draft'
UPDATE_JSON_URL = 'https://raw.githubusercontent.com/z2x3c4v5bz/project-i2c-expert-smart-battery-data-center/main/update.json'


class ProgressDialog(tk.Toplevel):
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

    Requested UX:
      - No extra Close button (close via window [X]).
      - Center on main window.
    """

    def __init__(self, master: 'App', field: str, title: str, prompt: str, initial: str = ''):
        super().__init__(master)
        self.app = master
        self.field = field

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
        self.app._last_search[self.field] = q
        self.app.find_in_view(self.field, q, direction)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('I2C Expert Smart Battery Data Center')
        self.geometry('1540x920')
        self.minsize(1320, 820)
        try:
            self.state('zoomed')
        except Exception:
            pass

        self.cfg: Optional[SbsConfig] = None
        self.cfg_path: Optional[str] = None
        self.log_path: Optional[str] = None
        self.records: List[ParsedRecord] = []

        self.filter_device: Optional[str] = None
        self.filter_cmd: Optional[str] = None
        self.hide_invalid: bool = False
        self.visible_indices: List[int] = []

        # Plot default hidden
        self.show_plot_var = tk.BooleanVar(value=False)

        self._last_search: Dict[str, str] = {}
        self._search_windows: Dict[str, SearchDialog] = {}

        self._build_menu()
        self._build_layout()
        self._set_menu_state()

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='New SBS Config', command=self.on_new_config)
        file_menu.add_command(label='Load SBS Config', command=self.on_load_config)
        file_menu.add_command(label='Load Log', command=self.on_load_log)
        file_menu.add_command(label='Save Photo...', command=self.on_save_photo)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.destroy)
        menubar.add_cascade(label='File', menu=file_menu)
        self.file_menu = file_menu

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label='Modify SBS Config', command=self.on_modify_config)
        edit_menu.add_separator()

        search_menu = tk.Menu(edit_menu, tearoff=0)
        search_menu.add_command(label='Search Command Code...', command=lambda: self.open_search_dialog('cmd'))
        search_menu.add_command(label='Search Raw Data...', command=lambda: self.open_search_dialog('raw'))
        search_menu.add_command(label='Search RW...', command=lambda: self.open_search_dialog('rw'))
        search_menu.add_separator()
        search_menu.add_command(label='Go to Index...', command=self.on_goto_index)
        edit_menu.add_cascade(label='Search', menu=search_menu)

        menubar.add_cascade(label='Edit', menu=edit_menu)
        self.edit_menu = edit_menu

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_checkbutton(label='Show Plot', variable=self.show_plot_var, command=self.on_toggle_plot)
        menubar.add_cascade(label='View', menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label='About', command=self.on_about)
        help_menu.add_command(label='Check Update', command=self.on_check_update)
        menubar.add_cascade(label='Help', menu=help_menu)

        self.config(menu=menubar)

    def _build_layout(self):
        topbar = ttk.Frame(self)
        topbar.pack(fill='x', padx=10, pady=6)

        ttk.Label(topbar, text='Loaded SBS Config:').pack(side='left')
        self.cfg_name_var = tk.StringVar(value='(None)')
        ttk.Label(topbar, textvariable=self.cfg_name_var, foreground='#1d4ed8').pack(side='left', padx=6)

        ttk.Label(topbar, text='|').pack(side='left', padx=6)
        ttk.Label(topbar, text='Loaded Log:').pack(side='left')
        self.log_name_var = tk.StringVar(value='(None)')
        ttk.Label(topbar, textvariable=self.log_name_var, foreground='#1d4ed8').pack(side='left', padx=6)

        ttk.Label(topbar, text='|').pack(side='left', padx=6)
        ttk.Label(topbar, text='Filter Status:').pack(side='left')
        self.filter_summary_var = tk.StringVar(value='(none)')
        ttk.Label(topbar, textvariable=self.filter_summary_var).pack(side='left', padx=6)

        ttk.Label(topbar, text='|').pack(side='left', padx=6)
        self.count_var = tk.StringVar(value='0/0')
        ttk.Label(topbar, textvariable=self.count_var).pack(side='left', padx=6)

        ttk.Button(topbar, text='Refresh Table', command=self.on_refresh_table).pack(side='right')

        fbar = ttk.LabelFrame(self, text='Filters')
        fbar.pack(fill='x', padx=10, pady=(0, 8))

        ttk.Label(fbar, text='Device Address (hex):').pack(side='left', padx=(10, 4))
        self.dev_entry = ttk.Entry(fbar, width=10)
        self.dev_entry.pack(side='left', padx=4)

        ttk.Label(fbar, text='Command Code (hex):').pack(side='left', padx=(14, 4))
        self.cmd_entry = ttk.Entry(fbar, width=12)
        self.cmd_entry.pack(side='left', padx=4)

        self.hide_invalid_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(fbar, text='Hide Invalid', variable=self.hide_invalid_var, command=self.on_apply_filters).pack(side='left', padx=(14, 4))

        ttk.Button(fbar, text='Apply', command=self.on_apply_filters).pack(side='left', padx=6)
        ttk.Button(fbar, text='Clear', command=self.on_clear_filters).pack(side='left', padx=6)

        main = ttk.PanedWindow(self, orient='vertical')
        main.pack(fill='both', expand=True, padx=10, pady=10)

        self.top = ttk.Frame(main)
        main.add(self.top, weight=3)

        self.bottom = ttk.PanedWindow(main, orient='horizontal')
        main.add(self.bottom, weight=2)

        cols = ('Index', 'Time', 'RW', 'ACK/NACK', 'Device Address', 'Command Code', 'Function', 'Value', 'Unit', 'Data')
        self.tree = ttk.Treeview(self.top, columns=cols, show='headings', height=18)
        for c in cols:
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

        ysb = ttk.Scrollbar(self.top, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.grid(row=0, column=1, sticky='ns')

        xsb = ttk.Scrollbar(self.top, orient='horizontal', command=self.tree.xview)
        self.tree.configure(xscroll=xsb.set)
        xsb.grid(row=1, column=0, sticky='ew')

        self.top.rowconfigure(0, weight=1)
        self.top.columnconfigure(0, weight=1)

        self.tree.bind('<<TreeviewSelect>>', self.on_select_record)

        # Bit Field
        self.bf_frame = ttk.LabelFrame(self.bottom, text='Bit Field')
        self.bottom.add(self.bf_frame, weight=1)

        self.bf_canvas = tk.Canvas(self.bf_frame, highlightthickness=0)
        self.bf_ysb = ttk.Scrollbar(self.bf_frame, orient='vertical', command=self.bf_canvas.yview)
        self.bf_xsb = ttk.Scrollbar(self.bf_frame, orient='horizontal', command=self.bf_canvas.xview)
        self.bf_canvas.configure(yscrollcommand=self.bf_ysb.set, xscrollcommand=self.bf_xsb.set)

        self.bf_canvas.grid(row=0, column=0, sticky='nsew')
        self.bf_ysb.grid(row=0, column=1, sticky='ns')
        self.bf_xsb.grid(row=1, column=0, sticky='ew')

        self.bf_frame.rowconfigure(0, weight=1)
        self.bf_frame.columnconfigure(0, weight=1)

        self.bit_container = ttk.Frame(self.bf_canvas)
        self.bf_canvas.create_window((0, 0), window=self.bit_container, anchor='nw')
        self.bit_container.bind('<Configure>', lambda e: self.bf_canvas.configure(scrollregion=self.bf_canvas.bbox('all')))

        # Plot
        self.plot_frame = ttk.LabelFrame(self.bottom, text='Plot')
        self.bottom.add(self.plot_frame, weight=2)

        controls = ttk.Frame(self.plot_frame)
        controls.pack(fill='x', padx=8, pady=(8, 4))

        self.plot_vars = {
            'Voltage()': tk.BooleanVar(value=True),
            'Current()': tk.BooleanVar(value=True),
            'RelativeStateOfCharge()': tk.BooleanVar(value=True),
        }
        for k, var in self.plot_vars.items():
            ttk.Checkbutton(controls, text=k, variable=var, command=self.refresh_plot).pack(side='left', padx=6)

        ttk.Label(controls, text='Plot Range (s):').pack(side='left', padx=(14, 4))
        self.plot_xmin_var = tk.StringVar(value='')
        self.plot_xmax_var = tk.StringVar(value='')
        ttk.Entry(controls, textvariable=self.plot_xmin_var, width=8).pack(side='left')
        ttk.Label(controls, text='~').pack(side='left', padx=4)
        ttk.Entry(controls, textvariable=self.plot_xmax_var, width=8).pack(side='left')

        ttk.Button(controls, text='Refresh Plot', command=self.refresh_plot).pack(side='right')

        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)

        render_plot(self.fig, [])
        self.canvas.draw()

        self._render_bitfield(None)

        # Hide plot by default
        if not self.show_plot_var.get():
            try:
                self.bottom.forget(self.plot_frame)
            except Exception:
                pass

    def _set_menu_state(self):
        if self.cfg is None:
            self.file_menu.entryconfig('Load Log', state='disabled')
            self.file_menu.entryconfig('Save Photo...', state='disabled')
            self.edit_menu.entryconfig('Modify SBS Config', state='disabled')
        else:
            self.file_menu.entryconfig('Load Log', state='normal')
            self.file_menu.entryconfig('Save Photo...', state='normal')
            self.edit_menu.entryconfig('Modify SBS Config', state='normal')

    # ---------- Actions ----------
    def on_new_config(self):
        try:
            from pathlib import Path
            p = Path(__file__).resolve().parent.parent / 'assets' / 'default_sbs_config.json'
            self.cfg = load_config(p)
            self.cfg_name_var.set(p.name)
            self.cfg_path = str(p)
            messagebox.showinfo('Config', 'New config created from default template.')
            self._set_menu_state()
        except Exception as e:
            messagebox.showerror('Error', f'Failed to create new config: {e}')

    def on_load_config(self):
        path = filedialog.askopenfilename(parent=self, title='Load SBS Config', filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            self.cfg = load_config(path)
            self.cfg_path = path
            self.cfg_name_var.set(path.split('/')[-1])
            messagebox.showinfo('Config', f'Loaded config: {path}')
            self._set_menu_state()
        except SbsConfigError as e:
            messagebox.showerror('Config Error', str(e))
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load config: {e}')

    def on_modify_config(self):
        if self.cfg is None:
            return
        editor = ConfigEditor(self, self.cfg)
        self.wait_window(editor)

    def on_load_log(self):
        if self.cfg is None:
            return
        path = filedialog.askopenfilename(parent=self, title='Load I2C Expert Log', filetypes=[('Text', '*.txt'), ('All', '*.*')])
        if not path:
            return
        self.log_path = path
        self.log_name_var.set(path.split('/')[-1])
        self._parse_current_log(show_message=True)

    def on_save_photo(self):
        if self.fig is None:
            messagebox.showwarning('Save Photo', 'No plot available.', parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, title='Save Photo', defaultextension='.png', filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg;*.jpeg'), ('All', '*.*')])
        if not path:
            return
        try:
            self.fig.savefig(path, dpi=200, bbox_inches='tight')
            messagebox.showinfo('Save Photo', f'Saved: {path}', parent=self)
        except Exception as e:
            messagebox.showerror('Save Photo', str(e), parent=self)

    def on_refresh_table(self):
        if self.log_path is None:
            messagebox.showwarning('Refresh', 'No log file loaded.', parent=self)
            return
        if self.cfg is None:
            messagebox.showwarning('Refresh', 'No SBS config loaded.', parent=self)
            return
        self._parse_current_log(show_message=False)

    def on_toggle_plot(self):
        if self.show_plot_var.get():
            try:
                if self.plot_frame.winfo_manager() == '':
                    self.bottom.add(self.plot_frame, weight=2)
            except Exception:
                pass
        else:
            try:
                self.bottom.forget(self.plot_frame)
            except Exception:
                pass

    # ---------- Filters ----------
    def on_apply_filters(self):
        dev = self.dev_entry.get().strip()
        cmd = self.cmd_entry.get().strip()

        self.filter_device = dev.upper() if dev else None

        if cmd:
            try:
                self.filter_cmd = f"0x{int(cmd, 16):02X}"
            except Exception:
                messagebox.showerror('Filter', 'Invalid Command Code hex value.', parent=self)
                return
        else:
            self.filter_cmd = None

        self.hide_invalid = bool(self.hide_invalid_var.get())
        self.apply_filters_and_refresh()

    def on_clear_filters(self):
        self.filter_device = None
        self.filter_cmd = None
        self.hide_invalid = False
        self.hide_invalid_var.set(False)
        self.dev_entry.delete(0, 'end')
        self.cmd_entry.delete(0, 'end')
        self.apply_filters_and_refresh()

    # ---------- Parsing ----------
    def _parse_current_log(self, show_message: bool):
        if self.log_path is None or self.cfg is None:
            return
        dlg = ProgressDialog(self, 'Parsing log...')

        def worker():
            try:
                with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                self.records = parse_log_lines(lines, self.cfg)
                self.after(0, lambda: self._on_log_parsed(dlg, show_message))
            except Exception as e:
                self.after(0, lambda: self._on_log_error(dlg, e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_log_parsed(self, dlg: ProgressDialog, show_message: bool):
        dlg.close()
        self.visible_indices = list(range(len(self.records)))
        self.apply_filters_and_refresh()
        self.refresh_plot()
        if show_message:
            messagebox.showinfo('Log', f'Loaded and parsed. Records: {len(self.records)}')

    def _on_log_error(self, dlg: ProgressDialog, err: Exception):
        dlg.close()
        messagebox.showerror('Log Error', str(err))

    def apply_filters_and_refresh(self):
        vis: List[int] = []
        for i, r in enumerate(self.records):
            if self.hide_invalid and (not r.is_valid):
                continue
            if self.filter_device:
                if (r.device_address or '').upper() != self.filter_device:
                    continue
            if self.filter_cmd:
                if not r.is_valid:
                    continue
                try:
                    cc = f"0x{int(r.command_code, 16):02X}"
                except Exception:
                    cc = ''
                if cc != self.filter_cmd:
                    continue
            vis.append(i)

        self.visible_indices = vis
        self._update_filter_summary()
        self.refresh_table()

    def _update_filter_summary(self):
        parts = []
        if self.filter_device:
            parts.append(f"Dev={self.filter_device}")
        if self.filter_cmd:
            parts.append(f"Cmd={self.filter_cmd}")
        parts.append('HideInvalid' if self.hide_invalid else 'ShowInvalid')

        total = len(self.records)
        visible = len(self.visible_indices)
        self.filter_summary_var.set(', '.join(parts) if parts else '(none)')
        self.count_var.set(f"{visible}/{total}")

    # ---------- Table ----------
    def refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        if not self.records:
            return

        for view_row, idx in enumerate(self.visible_indices):
            r = self.records[idx]
            time_str = format_time_us_to_hhmmssus(r.time_us) if (r.time_us is not None) else ''
            ack_str = 'NA' if (r.is_valid and r.is_nack) else ('A' if r.is_valid else '')

            cmd_str = ''
            if r.is_valid:
                try:
                    cmd_str = f"0x{int(r.command_code, 16):02X}"
                except Exception:
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

    def on_select_record(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            self._render_bitfield(None)
            return
        view_row = int(sel[0])
        if view_row < 0 or view_row >= len(self.visible_indices):
            self._render_bitfield(None)
            return
        idx = self.visible_indices[view_row]
        self._render_bitfield(self.records[idx])

    # ---------- Bit Field ----------
    def _render_bitfield(self, rec: Optional[ParsedRecord]):
        for w in self.bit_container.winfo_children():
            w.destroy()

        if rec is None or self.cfg is None:
            ttk.Label(self.bit_container, text='(No selection)').pack(anchor='w')
            return
        if not rec.is_valid:
            ttk.Label(self.bit_container, text='(Invalid record)').pack(anchor='w')
            return

        try:
            cc_norm = f"0x{int(rec.command_code, 16):02X}"
        except Exception:
            cc_norm = ''
        if not cc_norm or cc_norm not in self.cfg.body:
            ttk.Label(self.bit_container, text='(No bit-field definition)').pack(anchor='w')
            return

        d = self.cfg.body[cc_norm]
        if d.is_value or not d.bitfield:
            ttk.Label(self.bit_container, text='(No bit-field definition)').pack(anchor='w')
            return

        CELL_W = 14
        n = len(rec.bytes_le)
        if n <= 0:
            ttk.Label(self.bit_container, text='(No byte data)').pack(anchor='w')
            return

        # Display high byte first (byte index is list index because bytes_le is low->high)
        for bi in range(n - 1, -1, -1):
            b = rec.bytes_le[bi]
            frame = ttk.LabelFrame(self.bit_container, text=f'Byte {bi}')
            frame.pack(fill='x', pady=6)

            for col in range(8):
                frame.columnconfigure(col, weight=0)

            for col, bit in enumerate(range(7, -1, -1)):
                idx = bi * 8 + bit
                title = d.bitfield.get(str(idx), f'bit{idx}')
                ttk.Label(frame, text=title, width=CELL_W, anchor='center', borderwidth=1, relief='solid').grid(row=0, column=col, sticky='nsew', padx=1, pady=1)

            for col, bit in enumerate(range(7, -1, -1)):
                val = (b >> bit) & 1
                ttk.Label(frame, text=str(val), width=CELL_W, anchor='center', borderwidth=1, relief='solid').grid(row=1, column=col, sticky='nsew', padx=1, pady=1)

    # ---------- Search ----------
    def open_search_dialog(self, field: str):
        if not self.records or not self.visible_indices:
            return

        # Default selection to first row if none
        if not self.tree.selection() and self.visible_indices:
            self.tree.selection_set('0')
            self.tree.see('0')
            self.on_select_record()

        titles = {'cmd': 'Search Command Code', 'raw': 'Search Raw Data', 'rw': 'Search RW'}
        prompts = {'cmd': 'Enter Command Code (hex, e.g., 2D or 0x2D):', 'raw': 'Enter Raw Data keyword:', 'rw': 'Enter RW (R or W):'}
        initial = self._last_search.get(field, '')

        # Single window per field
        if field in self._search_windows:
            win = self._search_windows[field]
            try:
                if win.winfo_exists():
                    win.deiconify(); win.lift(); return
            except Exception:
                pass

        win = SearchDialog(self, field, titles[field], prompts[field], initial)
        self._search_windows[field] = win

    def _current_view_row(self) -> int:
        sel = self.tree.selection()
        if not sel:
            return -1
        try:
            return int(sel[0])
        except Exception:
            return -1

    def _match_record(self, idx: int, field: str, query: str) -> bool:
        r = self.records[idx]
        q = query.strip()

        if field == 'cmd':
            if not r.is_valid:
                return False
            try:
                cc = f"0x{int(r.command_code, 16):02X}"
            except Exception:
                cc = (r.command_code or '').upper()
            try:
                qn = f"0x{int(q, 16):02X}" if not q.lower().startswith('0x') else f"0x{int(q, 16):02X}"
            except Exception:
                qn = q.upper()
            return cc.upper() == qn.upper()

        if field == 'rw':
            return (r.rw or '').upper() == q.upper()

        return q.lower() in (r.data_raw or '').lower()

    def find_in_view(self, field: str, query: str, direction: int):
        if not self.records or not self.visible_indices:
            return

        n = len(self.visible_indices)
        cur = self._current_view_row()
        if cur < 0:
            cur = 0

        start = (cur + direction) % n
        steps = 0
        pos = start
        while steps < n:
            rec_idx = self.visible_indices[pos]
            if self._match_record(rec_idx, field, query):
                iid = str(pos)
                self.tree.selection_set(iid)
                self.tree.see(iid)
                self.on_select_record()
                return
            pos = (pos + direction) % n
            steps += 1

        messagebox.showinfo('Search', 'No match found after searching all records (within current filters).', parent=self)

    def on_goto_index(self):
        if not self.records:
            return
        q = simpledialog.askstring('Go to Index', 'Enter record index (0-based integer):', parent=self)
        if q is None or q.strip() == '':
            return
        try:
            idx = int(q.strip())
        except Exception:
            messagebox.showerror('Go to Index', 'Invalid integer index.', parent=self)
            return

        if idx < 0 or idx >= len(self.records):
            messagebox.showwarning('Go to Index', 'Index out of range.', parent=self)
            return

        if idx not in self.visible_indices:
            if messagebox.askyesno('Go to Index', 'This record is currently filtered out. Clear filters to show it?', parent=self):
                self.on_clear_filters()
            else:
                return

        pos = self.visible_indices.index(idx)
        iid = str(pos)
        self.tree.selection_set(iid)
        self.tree.see(iid)
        self.on_select_record()

    # ---------- Plot ----------
    def refresh_plot(self):
        if not self.records:
            render_plot(self.fig, [])
            self.canvas.draw()
            return

        targets: Dict[str, Tuple[str, str]] = {}
        if self.plot_vars['Voltage()'].get():
            targets['Voltage()'] = ('Voltage', 'mV')
        if self.plot_vars['Current()'].get():
            targets['Current()'] = ('Current', 'mA')
        if self.plot_vars['RelativeStateOfCharge()'].get():
            targets['RelativeStateOfCharge()'] = ('RSOC', '%')

        x_range = None
        try:
            xmin_txt = self.plot_xmin_var.get().strip()
            xmax_txt = self.plot_xmax_var.get().strip()
            if xmin_txt != '' or xmax_txt != '':
                xmin = float(xmin_txt) if xmin_txt != '' else float('-inf')
                xmax = float(xmax_txt) if xmax_txt != '' else float('inf')
                x_range = (xmin, xmax)
        except Exception:
            x_range = None

        series = build_series(self.records, targets, x_range=x_range)
        render_plot(self.fig, series)
        self.canvas.draw()

    # ---------- Help ----------
    def on_about(self):
        messagebox.showinfo('About', f'I2C Expert Smart Battery Data Center\nVersion: {APP_VERSION}\nUI: tkinter\nPlot: matplotlib')

    def on_check_update(self):
        res = check_update(UPDATE_JSON_URL, APP_VERSION)
        if res.ok:
            messagebox.showinfo('Update', res.message)
        else:
            messagebox.showwarning('Update', res.message)


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()

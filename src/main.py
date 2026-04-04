from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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

APP_VERSION = '0.3.0-draft'
UPDATE_JSON_URL = ''


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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('I2C Expert Smart Battery Data Center')
        self.geometry('1540x920')
        self.minsize(1320, 820)

        self.cfg: Optional[SbsConfig] = None
        self.cfg_path: Optional[str] = None
        self.log_path: Optional[str] = None
        self.records: List[ParsedRecord] = []

        self.filter_device: Optional[str] = None
        self.filter_cmd: Optional[str] = None
        self.hide_invalid: bool = False

        self.visible_indices: List[int] = []

        self._build_menu()
        self._build_layout()
        self._set_menu_state()

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='New SBS Config', command=self.on_new_config)
        file_menu.add_command(label='Load SBS Config', command=self.on_load_config)
        file_menu.add_command(label='Load Log', command=self.on_load_log)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.destroy)
        menubar.add_cascade(label='File', menu=file_menu)
        self.file_menu = file_menu

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label='Modify SBS Config', command=self.on_modify_config)
        edit_menu.add_separator()

        edit_menu.add_command(label='Filter: Device Address...', command=self.on_filter_device)
        edit_menu.add_command(label='Clear Device Address Filter', command=self.on_clear_filter_device)
        edit_menu.add_separator()

        edit_menu.add_command(label='Filter: Command Code...', command=self.on_filter_command)
        edit_menu.add_command(label='Clear Command Code Filter', command=self.on_clear_filter_command)
        edit_menu.add_separator()

        self.hide_invalid_var = tk.BooleanVar(value=False)
        edit_menu.add_checkbutton(label='Hide Invalid Records', variable=self.hide_invalid_var, command=self.on_toggle_hide_invalid)
        edit_menu.add_separator()

        search_menu = tk.Menu(edit_menu, tearoff=0)
        search_menu.add_command(label='Search: Command Code...', command=self.on_search_command)
        search_menu.add_command(label='Search: Raw Data...', command=self.on_search_raw)
        edit_menu.add_cascade(label='Search', menu=search_menu)

        menubar.add_cascade(label='Edit', menu=edit_menu)
        self.edit_menu = edit_menu

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
        ttk.Label(topbar, text='Filters:').pack(side='left')
        self.filter_summary_var = tk.StringVar(value='(none)')
        ttk.Label(topbar, textvariable=self.filter_summary_var).pack(side='left', padx=6)

        ttk.Button(topbar, text='Refresh Table', command=self.on_refresh_table).pack(side='right')

        main = ttk.PanedWindow(self, orient='vertical')
        main.pack(fill='both', expand=True, padx=10, pady=10)

        top = ttk.Frame(main)
        main.add(top, weight=3)

        bottom = ttk.PanedWindow(main, orient='horizontal')
        main.add(bottom, weight=2)

        cols = ('Time', 'RW', 'ACK/NACK', 'Device Address', 'Command Code', 'Function', 'Value', 'Unit', 'Data')
        self.tree = ttk.Treeview(top, columns=cols, show='headings', height=18)
        for c in cols:
            self.tree.heading(c, text=c)
            if c == 'Data':
                self.tree.column(c, width=620, anchor='w')
            elif c == 'Function':
                self.tree.column(c, width=260, anchor='w')
            elif c == 'Command Code':
                self.tree.column(c, width=120, anchor='w')
            elif c == 'ACK/NACK':
                self.tree.column(c, width=90, anchor='center')
            elif c == 'Time':
                self.tree.column(c, width=140, anchor='w')
            else:
                self.tree.column(c, width=130, anchor='w')
        self.tree.grid(row=0, column=0, sticky='nsew')

        ysb = ttk.Scrollbar(top, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.grid(row=0, column=1, sticky='ns')

        xsb = ttk.Scrollbar(top, orient='horizontal', command=self.tree.xview)
        self.tree.configure(xscroll=xsb.set)
        xsb.grid(row=1, column=0, sticky='ew')

        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)

        self.tree.bind('<<TreeviewSelect>>', self.on_select_record)

        bf_frame = ttk.LabelFrame(bottom, text='Bit Field')
        bottom.add(bf_frame, weight=1)

        self.bf_canvas = tk.Canvas(bf_frame, highlightthickness=0)
        self.bf_canvas.pack(side='left', fill='both', expand=True)

        bf_ysb = ttk.Scrollbar(bf_frame, orient='vertical', command=self.bf_canvas.yview)
        bf_ysb.pack(side='left', fill='y')
        self.bf_canvas.configure(yscrollcommand=bf_ysb.set)

        bf_xsb = ttk.Scrollbar(bf_frame, orient='horizontal', command=self.bf_canvas.xview)
        bf_xsb.pack(side='bottom', fill='x')
        self.bf_canvas.configure(xscrollcommand=bf_xsb.set)

        self.bit_container = ttk.Frame(self.bf_canvas)
        self.bf_canvas.create_window((0, 0), window=self.bit_container, anchor='nw')
        self.bit_container.bind('<Configure>', lambda e: self.bf_canvas.configure(scrollregion=self.bf_canvas.bbox('all')))

        plot_frame = ttk.LabelFrame(bottom, text='Plot')
        bottom.add(plot_frame, weight=2)

        controls = ttk.Frame(plot_frame)
        controls.pack(fill='x', padx=8, pady=(8, 4))

        self.plot_vars = {
            'Voltage()': tk.BooleanVar(value=True),
            'Current()': tk.BooleanVar(value=True),
            'RelativeStateOfCharge()': tk.BooleanVar(value=True),
        }
        for k, var in self.plot_vars.items():
            ttk.Checkbutton(controls, text=k, variable=var, command=self.refresh_plot).pack(side='left', padx=6)

        ttk.Button(controls, text='Refresh Plot', command=self.refresh_plot).pack(side='right')

        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)

        render_plot(self.fig, [])
        self.canvas.draw()

        self._render_bitfield(None)

    def _set_menu_state(self):
        if self.cfg is None:
            self.file_menu.entryconfig('Load Log', state='disabled')
            self.edit_menu.entryconfig('Modify SBS Config', state='disabled')
        else:
            self.file_menu.entryconfig('Load Log', state='normal')
            self.edit_menu.entryconfig('Modify SBS Config', state='normal')

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

    def on_refresh_table(self):
        if self.log_path is None:
            messagebox.showwarning('Refresh', 'No log file loaded.', parent=self)
            return
        if self.cfg is None:
            messagebox.showwarning('Refresh', 'No SBS config loaded.', parent=self)
            return
        self._parse_current_log(show_message=False)

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
        self.apply_filters_and_refresh()
        self.refresh_plot()
        if show_message:
            messagebox.showinfo('Log', f'Loaded and parsed. Records: {len(self.records)}')

    def _on_log_error(self, dlg: ProgressDialog, err: Exception):
        dlg.close()
        messagebox.showerror('Log Error', str(err))

    def on_filter_device(self):
        q = tk.simpledialog.askstring('Filter: Device Address', 'Enter hex (e.g., 16):', parent=self)
        if q is None:
            return
        q = q.strip()
        self.filter_device = q.upper() if q else None
        self.apply_filters_and_refresh()

    def on_clear_filter_device(self):
        self.filter_device = None
        self.apply_filters_and_refresh()

    def on_filter_command(self):
        q = tk.simpledialog.askstring('Filter: Command Code', 'Enter hex (e.g., 2D or 0x2D):', parent=self)
        if q is None:
            return
        q = q.strip()
        if not q:
            self.filter_cmd = None
        else:
            try:
                self.filter_cmd = f"0x{int(q, 16):02X}"
            except Exception:
                messagebox.showerror('Filter', 'Invalid hex value.', parent=self)
                return
        self.apply_filters_and_refresh()

    def on_clear_filter_command(self):
        self.filter_cmd = None
        self.apply_filters_and_refresh()

    def on_toggle_hide_invalid(self):
        self.hide_invalid = bool(self.hide_invalid_var.get())
        self.apply_filters_and_refresh()

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
        if self.hide_invalid:
            parts.append('HideInvalid')
        self.filter_summary_var.set(', '.join(parts) if parts else '(none)')

    def on_search_command(self):
        if not self.records:
            return
        q = tk.simpledialog.askstring('Search: Command Code', 'Enter hex (e.g., 2D or 0x2D):', parent=self)
        if not q:
            return
        try:
            qn = f"0x{int(q, 16):02X}"
        except Exception:
            messagebox.showerror('Search', 'Invalid hex value.', parent=self)
            return

        for view_row, idx in enumerate(self.visible_indices):
            r = self.records[idx]
            if not r.is_valid:
                continue
            try:
                cc = f"0x{int(r.command_code, 16):02X}"
            except Exception:
                cc = ''
            if cc == qn:
                iid = str(view_row)
                self.tree.selection_set(iid)
                self.tree.see(iid)
                self.on_select_record()
                return
        messagebox.showinfo('Search', 'No match found (within current filters).', parent=self)

    def on_search_raw(self):
        if not self.records:
            return
        q = tk.simpledialog.askstring('Search: Raw Data', 'Enter keyword (case-insensitive):', parent=self)
        if not q:
            return
        q = q.strip().lower()

        for view_row, idx in enumerate(self.visible_indices):
            r = self.records[idx]
            if q in (r.data_raw or '').lower():
                iid = str(view_row)
                self.tree.selection_set(iid)
                self.tree.see(iid)
                self.on_select_record()
                return
        messagebox.showinfo('Search', 'No match found (within current filters).', parent=self)

    def refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        if not self.visible_indices:
            self.visible_indices = list(range(len(self.records)))

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

        bits = []
        for bi, b in enumerate(rec.bytes_le):
            for bit in range(8):
                bits.append((bi * 8 + bit, (b >> bit) & 1))

        for bi in range(max(1, len(rec.bytes_le))):
            frame = ttk.LabelFrame(self.bit_container, text=f'Byte {bi}')
            frame.pack(fill='x', pady=6)
            hdr = ttk.Frame(frame)
            hdr.pack(fill='x')
            for bit in range(7, -1, -1):
                idx = bi * 8 + bit
                title = d.bitfield.get(str(idx), f'bit{idx}')
                ttk.Label(hdr, text=title, borderwidth=1, relief='solid', padding=3).pack(side='left', fill='x', expand=True)
            row = ttk.Frame(frame)
            row.pack(fill='x')
            for bit in range(7, -1, -1):
                idx = bi * 8 + bit
                val = 0
                for k, v in bits:
                    if k == idx:
                        val = v
                        break
                ttk.Label(row, text=str(val), borderwidth=1, relief='solid', padding=3).pack(side='left', fill='x', expand=True)

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

        series = build_series(self.records, targets)
        render_plot(self.fig, series)
        self.canvas.draw()

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

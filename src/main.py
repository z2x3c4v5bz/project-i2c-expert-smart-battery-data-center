from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Optional, List, Dict, Tuple

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .sbs_config import load_config
from .sbs_config import SbsConfig
from .sbs_config import SbsConfigError
from .log_parser import parse_log_lines
from .utils import format_time_us_to_hhmmssus, ParsedRecord
from .config_editor import ConfigEditor
from .plotter import build_series, render_plot
from .updater import check_update

APP_VERSION = '0.1.0-draft'

# Update check URL (GitHub raw URL). Keep empty by default.
UPDATE_JSON_URL = ''


class ProgressDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, text: str = 'Processing...'):
        super().__init__(master)
        self.title('Progress')
        self.geometry('420x120')
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', lambda: None)

        ttk.Label(self, text=text).pack(pady=(18, 8))
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
        self.geometry('1280x820')

        self.cfg: Optional[SbsConfig] = None
        self.cfg_path: Optional[str] = None
        self.records: List[ParsedRecord] = []

        self._build_menu()
        self._build_layout()
        self._set_menu_state()

    # ---------------- UI build ----------------
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
        edit_menu.add_command(label='Search', command=self.on_search)
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

        main = ttk.PanedWindow(self, orient='horizontal')
        main.pack(fill='both', expand=True, padx=10, pady=10)

        # Left: log list
        left = ttk.Frame(main)
        main.add(left, weight=3)

        cols = ('Time', 'RW', 'Device Address', 'Function', 'Value', 'Unit', 'Data')
        self.tree = ttk.Treeview(left, columns=cols, show='headings', height=22)
        for c in cols:
            self.tree.heading(c, text=c)
            if c == 'Data':
                self.tree.column(c, width=420, anchor='w')
            elif c == 'Function':
                self.tree.column(c, width=240, anchor='w')
            else:
                self.tree.column(c, width=120, anchor='w')
        self.tree.pack(side='left', fill='both', expand=True)

        ysb = ttk.Scrollbar(left, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.pack(side='left', fill='y')

        self.tree.bind('<<TreeviewSelect>>', self.on_select_record)

        # Right: bitfield + plot
        right = ttk.PanedWindow(main, orient='vertical')
        main.add(right, weight=2)

        bf_frame = ttk.LabelFrame(right, text='Bit Field')
        right.add(bf_frame, weight=1)

        self.bit_container = ttk.Frame(bf_frame)
        self.bit_container.pack(fill='both', expand=True, padx=8, pady=8)
        self._render_bitfield(None)

        plot_frame = ttk.LabelFrame(right, text='Plot')
        right.add(plot_frame, weight=2)

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

        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)

        render_plot(self.fig, [])
        self.canvas.draw()

    def _set_menu_state(self):
        # Load Log requires config
        if self.cfg is None:
            self.file_menu.entryconfig('Load Log', state='disabled')
            self.edit_menu.entryconfig('Modify SBS Config', state='disabled')
        else:
            self.file_menu.entryconfig('Load Log', state='normal')
            self.edit_menu.entryconfig('Modify SBS Config', state='normal')

    # ---------------- Menu callbacks ----------------
    def on_new_config(self):
        # Load from bundled default file
        try:
            import importlib.resources as res
            from pathlib import Path
            # fallback to assets path relative to project
            p = Path(__file__).resolve().parent.parent / 'assets' / 'default_sbs_config.json'
            self.cfg = load_config(p)
            self.cfg_name_var.set(p.name)
            self.cfg_path = str(p)
            messagebox.showinfo('Config', 'New config created from default template.')
            self._set_menu_state()
        except Exception as e:
            messagebox.showerror('Error', f'Failed to create new config: {e}')

    def on_load_config(self):
        path = filedialog.askopenfilename(
            parent=self,
            title='Load SBS Config',
            filetypes=[('JSON', '*.json')]
        )
        if not path:
            return
        try:
            self.cfg = load_config(path)
            self.cfg_path = path
            self.cfg_name_var.set(path.split('/')[-1])
            messagebox.showinfo('Config', f'Loaded config: {path}')
            self._set_menu_state()
            # If records already loaded, re-parse to refresh decoded view
            if self.records:
                self.refresh_table()
                self.refresh_plot()
        except SbsConfigError as e:
            messagebox.showerror('Config Error', str(e))
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load config: {e}')

    def on_modify_config(self):
        if self.cfg is None:
            return
        editor = ConfigEditor(self, self.cfg)
        self.wait_window(editor)
        # after editor close, refresh decoding
        if self.records:
            self.refresh_table()
            self.refresh_plot()

    def on_load_log(self):
        if self.cfg is None:
            return
        path = filedialog.askopenfilename(
            parent=self,
            title='Load I2C Expert Log',
            filetypes=[('Text', '*.txt'), ('All', '*.*')]
        )
        if not path:
            return

        dlg = ProgressDialog(self, 'Parsing log...')

        def worker():
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                recs = parse_log_lines(lines, self.cfg)
                self.records = recs
                self.after(0, lambda: self._on_log_loaded(dlg, path))
            except Exception as e:
                self.after(0, lambda: self._on_log_error(dlg, e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_log_loaded(self, dlg: ProgressDialog, path: str):
        dlg.close()
        self.refresh_table()
        self.refresh_plot()
        messagebox.showinfo('Log', f'Loaded and parsed: {path}\nRecords: {len(self.records)}')

    def _on_log_error(self, dlg: ProgressDialog, err: Exception):
        dlg.close()
        messagebox.showerror('Log Error', str(err))

    def on_search(self):
        if not self.records:
            return
        q = tk.simpledialog.askstring('Search', 'Enter keyword (Function/Raw Data):', parent=self)
        if not q:
            return
        q = q.strip().lower()
        # find first match
        for idx, r in enumerate(self.records):
            if q in (r.function or '').lower() or q in (r.data_raw or '').lower():
                iid = str(idx)
                self.tree.selection_set(iid)
                self.tree.see(iid)
                self.on_select_record()
                return
        messagebox.showinfo('Search', 'No match found.')

    def on_about(self):
        messagebox.showinfo('About', f'I2C Expert Smart Battery Data Center\nVersion: {APP_VERSION}\nUI: tkinter\nPlot: matplotlib')

    def on_check_update(self):
        res = check_update(UPDATE_JSON_URL, APP_VERSION)
        if res.ok:
            messagebox.showinfo('Update', res.message)
        else:
            messagebox.showwarning('Update', res.message)

    # ---------------- Table & selection ----------------
    def refresh_table(self):
        # Clear
        for i in self.tree.get_children():
            self.tree.delete(i)

        for idx, r in enumerate(self.records):
            time_str = format_time_us_to_hhmmssus(r.time_us) if (r.is_valid and r.time_us is not None) else ''
            self.tree.insert('', 'end', iid=str(idx), values=(
                time_str,
                r.rw,
                r.device_address,
                r.function,
                r.value_str,
                r.unit,
                r.data_raw,
            ))

    def on_select_record(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            self._render_bitfield(None)
            return
        idx = int(sel[0])
        r = self.records[idx]
        self._render_bitfield(r)

    # ---------------- Bit field view ----------------
    def _render_bitfield(self, rec: Optional[ParsedRecord]):
        for w in self.bit_container.winfo_children():
            w.destroy()

        if rec is None or not rec.is_valid or self.cfg is None:
            ttk.Label(self.bit_container, text='(No selection)').pack(anchor='w')
            return

        # Find definition
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

        # Build 16-bit bit list from bytes_le
        bits = []
        for bi, b in enumerate(rec.bytes_le):
            for bit in range(8):
                bits.append((bi * 8 + bit, (b >> bit) & 1))

        # Render per byte table
        for bi in range(max(1, len(rec.bytes_le))):
            frame = ttk.LabelFrame(self.bit_container, text=f'Byte {bi}')
            frame.pack(fill='x', pady=6)
            # header
            hdr = ttk.Frame(frame)
            hdr.pack(fill='x')
            # show 7..0 in display order
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

    # ---------------- Plot ----------------
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


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()

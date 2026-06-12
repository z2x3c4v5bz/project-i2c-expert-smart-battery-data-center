from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from typing import Dict

from ..app_state import AppState
from ..models.sbs import SbsConfigError
from ..services.config_io import create_default_config, load_config
from ..services.filter_engine import FilterSpec, apply as filter_apply
from ..services.log_parser import ParseOptions, parse_log_lines
from ..services.search_engine import SearchSpec, find as search_find
from ..services.updater import check_update
from ..utils import canonical_hex
from .bitfield_view import BitFieldView
from .config_editor import ConfigEditor
from .dialogs import ProgressDialog, SearchDialog
from .filter_bar import FilterBar
from .plot_panel import PlotPanel
from .table_view import RecordTableView

APP_VERSION = '0.9.0-draft'
UPDATE_JSON_URL = 'https://raw.githubusercontent.com/z2x3c4v5bz/project-i2c-expert-smart-battery-data-center/refs/heads/main/update.json'


class App(tk.Tk):
    """Slim coordinator: owns AppState, builds the layout, wires callbacks."""

    def __init__(self):
        super().__init__()
        self.title('I2C Expert Smart Battery Data Center')
        self.geometry('1540x920')
        self.minsize(1320, 820)
        try:
            self.state('zoomed')
        except Exception:
            pass

        self.state_data = AppState()

        self.show_plot_var = tk.BooleanVar(value=False)
        self._last_search: Dict[str, str] = {}
        self._search_windows: Dict[str, SearchDialog] = {}

        self._build_menu()
        self._build_layout()
        self._set_menu_state()

    # ---------- Menu ----------
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

    # ---------- Layout ----------
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

        self.filter_bar = FilterBar(
            self,
            on_apply=self.on_apply_filters,
            on_clear=self.on_clear_filters,
            on_time_format_change=self.on_time_format_change,
        )
        self.filter_bar.pack(fill='x', padx=10, pady=(0, 8))

        main = ttk.PanedWindow(self, orient='vertical')
        main.pack(fill='both', expand=True, padx=10, pady=10)

        self.table_view = RecordTableView(main, on_select=self.on_select_record)
        main.add(self.table_view, weight=3)

        self.bottom = ttk.PanedWindow(main, orient='horizontal')
        main.add(self.bottom, weight=2)

        self.bitfield_view = BitFieldView(self.bottom)
        self.bottom.add(self.bitfield_view, weight=1)

        self.plot_panel = PlotPanel(self.bottom, on_refresh=self.refresh_plot)
        self.bottom.add(self.plot_panel, weight=2)

        self.bitfield_view.render(None, None)

        # Hide plot by default
        if not self.show_plot_var.get():
            try:
                self.bottom.forget(self.plot_panel)
            except Exception:
                pass

    def _set_menu_state(self):
        state = 'disabled' if self.state_data.config is None else 'normal'
        self.file_menu.entryconfig('Load Log', state=state)
        self.file_menu.entryconfig('Save Photo...', state=state)
        self.edit_menu.entryconfig('Modify SBS Config', state=state)

    # ---------- File actions ----------
    def on_new_config(self):
        try:
            cfg = create_default_config()
            editor = ConfigEditor(self, cfg, is_new=True)
            self.wait_window(editor)
            if cfg.path is not None:  # Saved successfully
                self.state_data.config = cfg
                self.state_data.config_path = str(cfg.path)
                self.cfg_name_var.set(cfg.path.name)
                self._set_menu_state()
        except Exception as e:
            messagebox.showerror('Error', f'Failed to create new config: {e}')

    def on_load_config(self):
        path = filedialog.askopenfilename(parent=self, title='Load SBS Config', filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            self.state_data.config = load_config(path)
            self.state_data.config_path = path
            self.cfg_name_var.set(path.split('/')[-1])
            messagebox.showinfo('Config', f'Loaded config: {path}')
            self._set_menu_state()
        except SbsConfigError as e:
            messagebox.showerror('Config Error', str(e))
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load config: {e}')

    def on_modify_config(self):
        if self.state_data.config is None:
            return
        editor = ConfigEditor(self, self.state_data.config)
        self.wait_window(editor)

    def on_load_log(self):
        if self.state_data.config is None:
            return
        path = filedialog.askopenfilename(parent=self, title='Load I2C Expert Log', filetypes=[('Text', '*.txt'), ('All', '*.*')])
        if not path:
            return
        self.state_data.log_path = path
        self.log_name_var.set(path.split('/')[-1])
        self._parse_current_log(show_message=True)

    def on_save_photo(self):
        path = filedialog.asksaveasfilename(parent=self, title='Save Photo', defaultextension='.png', filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg;*.jpeg'), ('All', '*.*')])
        if not path:
            return
        try:
            self.plot_panel.save_photo(path)
            messagebox.showinfo('Save Photo', f'Saved: {path}', parent=self)
        except Exception as e:
            messagebox.showerror('Save Photo', str(e), parent=self)

    def on_refresh_table(self):
        if self.state_data.log_path is None:
            messagebox.showwarning('Refresh', 'No log file loaded.', parent=self)
            return
        if self.state_data.config is None:
            messagebox.showwarning('Refresh', 'No SBS config loaded.', parent=self)
            return
        self._parse_current_log(show_message=False)

    def on_toggle_plot(self):
        if self.show_plot_var.get():
            try:
                if self.plot_panel.winfo_manager() == '':
                    self.bottom.add(self.plot_panel, weight=2)
            except Exception:
                pass
        else:
            try:
                self.bottom.forget(self.plot_panel)
            except Exception:
                pass

    # ---------- Filters ----------
    def on_apply_filters(self):
        dev, cmd, hide = self.filter_bar.get_inputs()

        command_code = ''
        if cmd:
            try:
                command_code = canonical_hex(cmd)
            except ValueError:
                messagebox.showerror('Filter', 'Invalid Command Code hex value.', parent=self)
                return

        self.state_data.filter_spec = FilterSpec(
            device_address=dev.upper() if dev else '',
            command_code=command_code,
            hide_invalid=hide,
        )
        self.apply_filters_and_refresh()

    def on_clear_filters(self):
        self.state_data.filter_spec = FilterSpec()
        self.filter_bar.clear_inputs()
        self.apply_filters_and_refresh()

    def apply_filters_and_refresh(self):
        st = self.state_data
        st.visible_indices = filter_apply(st.filter_spec, st.all_records)
        self._update_filter_summary()
        self.table_view.populate(st.all_records, st.visible_indices)

    def _update_filter_summary(self):
        spec = self.state_data.filter_spec
        parts = []
        if spec.device_address:
            parts.append(f"Dev={spec.device_address.upper()}")
        if spec.command_code:
            parts.append(f"Cmd={spec.command_code}")
        parts.append('HideInvalid' if spec.hide_invalid else 'ShowInvalid')

        total = len(self.state_data.all_records)
        visible = len(self.state_data.visible_indices)
        self.filter_summary_var.set(', '.join(parts) if parts else '(none)')
        self.count_var.set(f"{visible}/{total}")

    # ---------- Parsing ----------
    def _parse_current_log(self, show_message: bool):
        st = self.state_data
        if st.log_path is None or st.config is None:
            return
        st.parse_options = ParseOptions(time_format=self.filter_bar.time_format)
        dlg = ProgressDialog(self, 'Parsing log...')

        def worker():
            try:
                with open(st.log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                records = parse_log_lines(lines, st.config, st.parse_options)
                self.after(0, lambda: self._on_log_parsed(dlg, records, show_message))
            except Exception as e:
                self.after(0, lambda: self._on_log_error(dlg, e))

        threading.Thread(target=worker, daemon=True).start()

    def on_time_format_change(self):
        if self.state_data.log_path is not None:
            self._parse_current_log(show_message=False)

    def _on_log_parsed(self, dlg: ProgressDialog, records, show_message: bool):
        dlg.close()
        self.state_data.all_records = records
        self.state_data.visible_indices = list(range(len(records)))
        self.apply_filters_and_refresh()
        self.refresh_plot()
        if show_message:
            messagebox.showinfo('Log', f'Loaded and parsed. Records: {len(records)}')

    def _on_log_error(self, dlg: ProgressDialog, err: Exception):
        dlg.close()
        messagebox.showerror('Log Error', str(err))

    # ---------- Selection / Bit Field ----------
    def on_select_record(self, _evt=None):
        view_row = self.table_view.current_view_row()
        st = self.state_data
        if view_row < 0 or view_row >= len(st.visible_indices):
            st.selected_index = None
            self.bitfield_view.render(None, st.config)
            return
        idx = st.visible_indices[view_row]
        st.selected_index = idx
        self.bitfield_view.render(st.all_records[idx], st.config)

    # ---------- Search ----------
    def open_search_dialog(self, field: str):
        st = self.state_data
        if not st.all_records or not st.visible_indices:
            return

        # Default selection to first row if none
        if not self.table_view.has_selection() and st.visible_indices:
            self.table_view.select_view_row(0)
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

        def on_find(direction: int, query: str):
            self._last_search[field] = query
            self.find_in_view(field, query, direction)

        win = SearchDialog(self, titles[field], prompts[field], initial, on_find)
        self._search_windows[field] = win

    def find_in_view(self, field: str, query: str, direction: int):
        st = self.state_data
        if not st.all_records or not st.visible_indices:
            return

        cur = self.table_view.current_view_row()
        if cur < 0:
            cur = 0

        spec = SearchSpec(field=field, query=query)
        pos = search_find(spec, st.visible_indices, st.all_records, cur, direction)
        if pos is None:
            messagebox.showinfo('Search', 'No match found after searching all records (within current filters).', parent=self)
            return

        self.table_view.select_view_row(pos)
        self.on_select_record()

    def on_goto_index(self):
        st = self.state_data
        if not st.all_records:
            return
        q = simpledialog.askstring('Go to Index', 'Enter record index (0-based integer):', parent=self)
        if q is None or q.strip() == '':
            return
        try:
            idx = int(q.strip())
        except ValueError:
            messagebox.showerror('Go to Index', 'Invalid integer index.', parent=self)
            return

        if idx < 0 or idx >= len(st.all_records):
            messagebox.showwarning('Go to Index', 'Index out of range.', parent=self)
            return

        if idx not in st.visible_indices:
            if messagebox.askyesno('Go to Index', 'This record is currently filtered out. Clear filters to show it?', parent=self):
                self.on_clear_filters()
            else:
                return

        pos = st.visible_indices.index(idx)
        self.table_view.select_view_row(pos)
        self.on_select_record()

    # ---------- Plot ----------
    def refresh_plot(self):
        self.plot_panel.refresh(self.state_data.all_records)

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

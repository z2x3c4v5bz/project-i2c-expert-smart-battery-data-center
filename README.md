# I2C Expert Smart Battery Data Center (v0.9 draft)

## Changes
- Value(binary) order fixed: for non-isValue entries, bytes are displayed high->low in the **Value** field.
- SBS Config Editor:
  - Window appears centered on screen when opened.
  - Minimize & Maximize buttons removed (Windows only).
  - FunctionType values now correctly match JSON (fixed int-key mapping).
- Search dialogs (Command Code / Raw Data / RW):
  - Removed extra **Close** button (close via window [X]).
  - Dialog appears centered on main window.
- Plot is hidden by default.
- Default SBS configuration is now embedded in the code, making the application more robust against missing asset files.
- New SBS Config now includes all 256 command codes (0x00 to 0xFF) with predefined values for known commands and "Reserved" defaults for others.

## Run
```bash
pip install -r requirements.txt
python -m main
```

## Build Executable
```bash
pip install pyinstaller
pyinstaller main.spec
```
The executable will be created in the `dist/` directory.

## Troubleshooting

### NumPy 2.x Import Error in Executable
If you encounter `No module named 'numpy._core._exceptions'` when running the built executable, this is due to NumPy 2.x compatibility with PyInstaller.

#### Recommended Solution:

1. Ensure you have the latest PyInstaller (>= 6.3):
   ```bash
   pip install --upgrade pyinstaller
   ```

2. Clean previous builds:
   ```bash
   rmdir /s build dist
   del main.spec
   ```

3. Regenerate and rebuild:
   ```bash
   pyinstaller main.spec
   ```

#### If errors persist:

1. Check if main.spec has correct `hiddenimports` and `hooksconfig` for numpy 2.x
2. Regenerate main.spec from scratch:
   ```bash
   pyinstaller --onefile --windowed --hidden-import=numpy._core._exceptions main.py
   ```

3. Manually edit main.spec if regenerated and add to the `Analysis()` call:
   ```python
   hooksconfig={
       'numpy': {'collect_all': True},
   },
   ```

### Alternative: Use NumPy 1.x
If you cannot upgrade PyInstaller, you can use NumPy 1.x instead:

1. Edit requirements.txt:
   ```
   matplotlib>=3.7
   numpy>=1.21,<2.0
   ```

2. Reinstall dependencies:
   ```bash
   pip uninstall numpy pyinstaller
   pip install -r requirements.txt pyinstaller
   ```

3. Rebuild the executable:
   ```bash
   pyinstaller main.spec
   ```

## Quick test
- Create new config: File > New SBS Config (uses embedded default template)
- Load log: assets/sample_log_snippet.txt
  - Voltage() bytes 96 2F => decimal 12182
  - BatteryStatus() bytes 01 80 => binary shown as "10000000 00000001" in Value (high->low)

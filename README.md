# I2C Expert Smart Battery Data Center (v0.8 draft)

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

## Run
```bash
pip install -r requirements.txt
python -m main
```

## Quick test
- Load config: assets/default_sbs_config.json
- Load log: assets/sample_log_snippet.txt
  - Voltage() bytes 96 2F => decimal 12182
  - BatteryStatus() bytes 01 80 => binary shown as "10000000 00000001" in Value (high->low)

# I2C Expert Smart Battery Data Center (v0.5 draft)

## Highlights
- Main table: added Index column (global index, not affected by filters)
- Search redesigned:
  - Find Next / Find Previous for Command Code, Raw Data, RW
  - Wrap-around search (top<->bottom); if no match after one full loop, notify user
  - Go to Index (exact定位, no wrap)
- Bit Field display: High byte on top, Low byte on bottom
- SBS Config Editor:
  - Resizable left list / right detail using PanedWindow (draggable sash)
  - Maximize/Restore enabled (resizable + OS window buttons)
  - BitField edit is buffered: changes take effect only after "Apply Changes"
  - Save / Save As writes to file; closing without saving prompts to Discard or Cancel

## Run
```bash
pip install -r requirements.txt
python -m src.main
```

## Test
- Load config: assets/default_sbs_config.json
- Load log: assets/sample_log_snippet.txt

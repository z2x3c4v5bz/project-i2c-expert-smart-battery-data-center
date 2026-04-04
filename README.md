# I2C Expert Smart Battery Data Center (v0.7 draft)

## Highlights
- **isValue decoding fixed**: decode uses low->high (little-endian) byte order before converting to decimal.
- Plot legend moved **outside to the right** to avoid covering the chart.
- Plot time range filter (seconds) added.
- File menu: **Save Photo...** to export current plot.
- Search menu simplified: Search Command/Raw/RW opens a dialog with **Find Previous/Find Next** buttons.
- Search dialog smaller width; no Cancel button.
- SBS Config Editor: no auto-maximize; maximize button disabled (Windows only).
- BitField edit: OK stores pending changes; switching command/closing prompts discard/cancel.

## Run
```bash
pip install -r requirements.txt
python -m src.main
```

## Test
- Load config: assets/default_sbs_config.json
- Load log: assets/sample_log_snippet.txt

# I2C Expert Smart Battery Data Center (v0.3 draft)

## Highlights
- Main window layout: Top = data table; Bottom-left = Bit Field; Bottom-right = Plot
- Main table columns include: ACK/NACK, Command Code
- Time always displayed when timestamp exists (even if record is invalid)
- Refresh Table button to re-parse current log after SBS config update
- Edit menu: filters (Device Address / Command Code), clear, hide invalid, split searches (Command Code / Raw Data)
- SBS Config Editor: Save (overwrite) with confirmation + uniqueness validation (FunctionType & Function, except Customize)
- BitField editor: Add/Update/Delete with dynamic bit index (0..1023)

## Run
```bash
pip install -r requirements.txt
python -m src.main
```

## Test
- Load config: assets/default_sbs_config.json
- Load log: assets/sample_log_snippet.txt

# I2C Expert Smart Battery Data Center (v0.4 draft)

## Highlights
- Valid record threshold: >= 1 data byte (instead of >= 2)
- Persistent filter toolbar (Device / Command / Hide Invalid)
- Filter status: multi-condition summary + visible/total count
- View menu added: Show/Hide plot
- Bit Field area: fixed x-scrollbar placement + fixed cell widths
- Main & Config Editor open maximized by default (BitFieldEditor stays normal)
- Parsing improvement: reverse data byte order before decoding (e.g., 01 E9 -> E9 01)

## Run
```bash
pip install -r requirements.txt
python -m src.main
```

## Test
- Load config: assets/default_sbs_config.json
- Load log: assets/sample_log_snippet.txt

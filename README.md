# I2C Expert Smart Battery Data Center (v0.2 draft)

## What's new in v0.2
- Main window layout: top = data table, bottom-left = bit field, bottom-right = plot
- Config editor: can jump to a specific Command Code (Go), and edit BitField via Add/Delete UI
- Config keys normalized to canonical format: 0xNN
- Log parser: more tolerant for delimiters like '----->' or '-----\>'

## Run
```bash
pip install -r requirements.txt
python -m src.main
```


# I2C Expert Smart Battery Data Center

> A desktop tool to parse I2C Expert log (.txt) and decode SMBus/Smart Battery commands via a JSON SBS configuration.

## Features
- Load/Edit SBS config (JSON)
- Load I2C Expert log (.txt) and parse Read/Write transactions
- Show decoded Function/Value/Unit and raw bytes
- Bit-field view (when IsValue = false)
- Plot Voltage/Current/RSOC vs time
- Manual update check (GitHub) — **disabled by default** (set URL in settings)

## Run
```bash
python -m src.main
```

## Notes
- Python 3.x
- UI: tkinter
- Plot: matplotlib


# I2C Expert Smart Battery Data Center (v0.9 draft)

## Changes
- Default SBS configuration is now embedded in the code, making the application more robust against missing asset files.
- New SBS Config now includes all 256 command codes (0x00 to 0xFF) with predefined values for known commands and "Reserved" defaults for others.
- Added main entry point (main.py) for easier execution.
- Enhanced update checking functionality with proper HTTP requests and JSON parsing.
- Updated version to v0.8.1.
- Fixed UPDATE_JSON_URL to use refs/heads for consistency.

## Run
```bash
pip install -r requirements.txt
python -m main
```

## Quick test
- Create new config: File > New SBS Config (uses embedded default template)

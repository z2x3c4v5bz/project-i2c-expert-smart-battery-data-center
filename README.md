# I2C Expert Smart Battery Data Center (v0.6 draft)

## Highlights
- Search menu simplified: Search Command/Raw/RW opens one dialog with Find Previous/Next buttons
- Search dialog uses current selection as anchor; defaults to first record if none selected
- Wrap-around search; stop with message if no match after one full loop
- Main table: Index column (global index, not affected by filters)
- Go to Index (exact定位)
- Byte order handling:
  - Log data tokens are low->high; we reverse to high->low for *new low->new high* mapping
  - isValue conversion uses reordered bytes before hex->decimal
- Bit Field display mapping fixed: high byte shown on top and bit indices align
- SBS Config Editor:
  - No default maximize on open
  - Maximize button enabled (do NOT set transient on editor)
  - BitField edits are pending after OK; must Apply Changes then Save/Save As
  - If pending BitField exists, switching Command or closing prompts Discard/Cancel

## Run
```bash
pip install -r requirements.txt
python -m src.main
```

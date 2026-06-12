"""Headless tests for the pure-logic core (no tkinter required).

Run with:  python -m tests.test_core   (or: pytest tests/)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.config_io import create_default_config, load_config, save_config  # noqa: E402
from src.services.filter_engine import FilterSpec, apply as filter_apply  # noqa: E402
from src.services.log_parser import ParseOptions, parse_log_lines  # noqa: E402
from src.services.plotter import build_series  # noqa: E402
from src.services import search_engine as se  # noqa: E402
from src.utils import canonical_hex  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / 'assets' / 'sample_log_snippet.txt'


def _records():
    cfg = create_default_config()
    lines = FIXTURE.read_text(encoding='utf-8').splitlines(keepends=True)
    return cfg, parse_log_lines(lines, cfg, ParseOptions(time_format='legacy'))


def test_canonical_hex():
    assert canonical_hex('2d') == '0x2D'
    assert canonical_hex('0x2d') == '0x2D'
    assert canonical_hex(9) == '0x09'
    try:
        canonical_hex('zz')
        raise AssertionError('expected ValueError')
    except ValueError:
        pass


def test_parse_voltage_write():
    _, recs = _records()
    r0 = recs[0]
    assert r0.is_valid and r0.rw == 'W'
    assert r0.command_code == '09'
    assert r0.function == 'Voltage()'
    assert r0.value_str == str(0x1234)  # little-endian 34 12 -> 0x1234


def test_parse_voltage_read():
    _, recs = _records()
    r1 = recs[1]
    assert r1.is_valid and r1.rw == 'R'
    assert r1.function == 'Voltage()'
    assert r1.value_str == str(0x1234)


def test_nack_detected():
    _, recs = _records()
    assert recs[4].is_nack is True


def test_invalid_line():
    _, recs = _records()
    assert recs[5].is_valid is False


def test_filter_hide_invalid():
    _, recs = _records()
    visible = filter_apply(FilterSpec(hide_invalid=True), recs)
    assert all(recs[i].is_valid for i in visible)
    assert len(visible) == sum(1 for r in recs if r.is_valid)


def test_filter_by_command():
    _, recs = _records()
    visible = filter_apply(FilterSpec(command_code=canonical_hex('0A')), recs)
    assert visible and all(canonical_hex(recs[i].command_code) == '0x0A' for i in visible)


def test_search_find_cmd_wraps():
    _, recs = _records()
    visible = list(range(len(recs)))
    spec = se.SearchSpec(field=se.FIELD_CMD, query='0D')
    pos = se.find(spec, visible, recs, start_pos=0, direction=1)
    assert pos is not None and recs[visible[pos]].command_code == '0D'


def test_build_series_voltage():
    _, recs = _records()
    series = build_series(recs, {'Voltage()': ('Voltage', 'mV')})
    volt = [s for s in series if s.name == 'Voltage'][0]
    assert len(volt.y) >= 1 and volt.y[0] == float(0x1234)


def test_config_roundtrip(tmp_path=None):
    import tempfile
    cfg = create_default_config()
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'cfg.json'
        save_config(cfg, p)
        cfg2 = load_config(p)
    assert cfg2.body['0x09'].function == 'Voltage()'
    assert len(cfg2.body) == len(cfg.body)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f'PASS {fn.__name__}')
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f'FAIL {fn.__name__}: {type(e).__name__}: {e}')
    print(f'\n{len(fns) - failed}/{len(fns)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(1 if _run_all() else 0)

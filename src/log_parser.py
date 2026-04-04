from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import re

from .utils import ParsedRecord, strip_us_unit, safe_int, normalize_hex_token
from .sbs_config import SbsConfig


@dataclass
class ParseOptions:
    device_addr_width: int = 2


# Accept delimiters like "----->" or "-----\\>" (backslash before >)
_ARROW_RE = re.compile(r"-{5,}\s*(?:>|\\>)")


def _split_time_and_payload(line: str) -> tuple[Optional[int], str, bool]:
    """Split a log line by arrow delimiter.

    The draft expects: <timestamp>us -----> <payload>
    Real logs may contain spaces and sometimes '-----\\>' due to escaping.

    Returns:
        (time_us, payload, ok)
    """
    m = _ARROW_RE.search(line)
    if not m:
        return None, line.strip(), False

    left = line[:m.start()].strip()
    right = line[m.end():].strip()

    ts = strip_us_unit(left)
    if not ts.isdigit():
        return None, right, False

    return safe_int(ts, 10, 0), right, True


def _count_markers(payload: str) -> tuple[int, int]:
    return payload.count('[S]'), payload.count('[P]')


def _extract_between(payload: str, start: str, end: str) -> str:
    s = payload.find(start)
    if s < 0:
        return ''
    s += len(start)
    e = payload.find(end, s)
    if e < 0:
        return ''
    return payload[s:e].strip()


def _extract_after(payload: str, start: str) -> str:
    s = payload.find(start)
    if s < 0:
        return ''
    s += len(start)
    return payload[s:].strip()


def _parse_hex_tokens(segment: str) -> List[str]:
    return [t for t in segment.split() if t]


def _bytes_from_tokens_reversed(tokens: List[str], start_idx: int) -> tuple[List[int], bool]:
    """Build byte list in little-endian order from token list."""
    if len(tokens) <= start_idx:
        return [], False

    is_nack = False
    out: List[int] = []
    for tok in reversed(tokens[start_idx:]):
        h, nack = normalize_hex_token(tok)
        is_nack = is_nack or nack
        try:
            out.append(int(h, 16))
        except Exception:
            return [], is_nack
    return out, is_nack


def _decode_value(bytes_le: List[int], is_value: bool) -> str:
    if not bytes_le:
        return ''
    if is_value:
        val = 0
        for i, b in enumerate(bytes_le):
            val |= (b & 0xFF) << (8 * i)
        return str(val)

    return ' '.join(f"{b:08b}" for b in bytes_le)


def parse_log_lines(lines: List[str], cfg: Optional[SbsConfig]) -> List[ParsedRecord]:
    records: List[ParsedRecord] = []

    for line in lines:
        raw = line.rstrip('\n')
        time_us, payload, has_time = _split_time_and_payload(raw)

        s_cnt, p_cnt = _count_markers(payload)
        is_valid = has_time and (p_cnt == 1) and (s_cnt in (1, 2))

        rw = ''
        device = ''
        cmd = ''
        function = ''
        unit = ''
        value_str = ''
        is_nack = False
        bytes_le: List[int] = []

        if is_valid:
            if s_cnt == 1:
                rw = 'W'
                seg = _extract_between(payload, '[S]', '[P]')
                toks = _parse_hex_tokens(seg)
                if len(toks) < 3:
                    is_valid = False
                else:
                    device = toks[0].upper()
                    cmd = toks[1].upper()
                    bytes_le, is_nack = _bytes_from_tokens_reversed(toks, 2)
                    if not bytes_le:
                        is_valid = False

            elif s_cnt == 2:
                rw = 'R'
                after_first = _extract_after(payload, '[S]')
                if '[S]' not in after_first:
                    is_valid = False
                else:
                    part1, part2 = after_first.split('[S]', 1)
                    toks1 = _parse_hex_tokens(part1)
                    toks2 = _parse_hex_tokens(_extract_between('[S]' + part2, '[S]', '[P]'))

                    if len(toks1) != 2:
                        is_valid = False
                    elif len(toks2) < 2:
                        is_valid = False
                    else:
                        device = toks1[0].upper()
                        cmd = toks1[1].upper()
                        bytes_le, is_nack = _bytes_from_tokens_reversed(toks2, 1)
                        if not bytes_le:
                            is_valid = False
            else:
                is_valid = False

        if is_valid and cfg is not None and cmd:
            try:
                cc_norm = f"0x{int(cmd, 16):02X}"
            except Exception:
                cc_norm = ''

            if cc_norm and cc_norm in cfg.body:
                d = cfg.body[cc_norm]
                function = d.function
                unit = d.unit
                value_str = _decode_value(bytes_le, d.is_value)
            else:
                function = 'Unknown'
                unit = 'NA'
                value_str = _decode_value(bytes_le, True)

        records.append(ParsedRecord(
            time_us=time_us if has_time else None,
            rw=rw if is_valid else '',
            device_address=device if is_valid else '',
            command_code=cmd if is_valid else '',
            function=function if is_valid else '',
            value_str=value_str if is_valid else '',
            unit=unit if is_valid else '',
            data_raw=payload if has_time else raw,
            is_valid=is_valid,
            is_nack=is_nack,
            bytes_le=bytes_le,
        ))

    return records

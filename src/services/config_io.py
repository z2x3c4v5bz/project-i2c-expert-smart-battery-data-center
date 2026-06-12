from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..models.sbs import FUNCTION_TYPE, SbsCommandDef, SbsConfig, SbsConfigError
from ..utils import canonical_hex


def validate_config_schema(obj: Dict[str, Any]) -> None:
    if not isinstance(obj, dict):
        raise SbsConfigError('Config root must be an object.')
    if 'Title' not in obj or 'Body' not in obj:
        raise SbsConfigError('Config must contain Title and Body.')
    if not isinstance(obj['Title'], str):
        raise SbsConfigError('Title must be a string.')
    if not isinstance(obj['Body'], dict):
        raise SbsConfigError('Body must be an object.')

    for cc, d in obj['Body'].items():
        if not isinstance(cc, str):
            raise SbsConfigError(f'Invalid command code key: {cc}')
        if not isinstance(d, dict):
            raise SbsConfigError(f'Command definition must be object: {cc}')
        for k in ['Function', 'FunctionType', 'Access', 'IsValue', 'Unit', 'BitField']:
            if k not in d:
                raise SbsConfigError(f'Missing {k} in {cc}')


def _command_def_from_dict(d: Dict[str, Any]) -> SbsCommandDef:
    """Build an SbsCommandDef from a raw JSON command object."""
    ft = int(d['FunctionType'])
    fn = str(d['Function'])
    if ft != 0:
        fn = FUNCTION_TYPE.get(ft, fn)

    bitfield = dict(d['BitField']) if isinstance(d['BitField'], dict) else {}

    return SbsCommandDef(
        function=fn,
        function_type=ft,
        access=int(d['Access']),
        is_value=bool(d['IsValue']),
        unit=str(d['Unit']),
        bitfield=bitfield,
    )


def load_config(path: str | Path) -> SbsConfig:
    p = Path(path)
    with p.open('r', encoding='utf-8') as f:
        obj = json.load(f)

    validate_config_schema(obj)

    body: Dict[str, SbsCommandDef] = {}
    for cc_raw, d in obj['Body'].items():
        body[canonical_hex(cc_raw)] = _command_def_from_dict(d)

    return SbsConfig(title=obj['Title'], body=body, path=p)


def save_config(cfg: SbsConfig, path: str | Path) -> None:
    p = Path(path)
    obj: Dict[str, Any] = {'Title': cfg.title, 'Body': {}}

    for cc in sorted(cfg.body.keys(), key=lambda x: int(x[2:], 16)):
        d = cfg.body[cc]
        obj['Body'][cc] = {
            'Function': d.function,
            'FunctionType': int(d.function_type),
            'Access': int(d.access),
            'IsValue': bool(d.is_value),
            'Unit': d.unit,
            'BitField': d.bitfield,
        }

    with p.open('w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)


# Default SBS configuration embedded in code (keeps the binary self-contained).
DEFAULT_SBS_CONFIG_DATA = {
    "Title": "Default SBS Config (Draft)",
    "Body": {
        "0x00": {"Function": "ManufacturerAccess()", "FunctionType": 1, "Access": 3, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0x01": {"Function": "RemainingCapacityAlarm()", "FunctionType": 2, "Access": 3, "IsValue": True, "Unit": "mAh or 10mWh", "BitField": {}},
        "0x02": {"Function": "RemainingTimeAlarm()", "FunctionType": 3, "Access": 3, "IsValue": True, "Unit": "min", "BitField": {}},
        "0x03": {"Function": "BatteryMode()", "FunctionType": 4, "Access": 3, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0x04": {"Function": "AtRate()", "FunctionType": 5, "Access": 3, "IsValue": True, "Unit": "mA or 10mW", "BitField": {}},
        "0x05": {"Function": "AtRateTimeToFull()", "FunctionType": 6, "Access": 1, "IsValue": True, "Unit": "min", "BitField": {}},
        "0x06": {"Function": "AtRateTimeToEmpty()", "FunctionType": 7, "Access": 1, "IsValue": True, "Unit": "min", "BitField": {}},
        "0x07": {"Function": "AtRateOK()", "FunctionType": 8, "Access": 1, "IsValue": True, "Unit": "Boolean", "BitField": {}},
        "0x08": {"Function": "Temperature()", "FunctionType": 9, "Access": 1, "IsValue": True, "Unit": "0.1K", "BitField": {}},
        "0x09": {"Function": "Voltage()", "FunctionType": 10, "Access": 1, "IsValue": True, "Unit": "mV", "BitField": {}},
        "0x0A": {"Function": "Current()", "FunctionType": 11, "Access": 1, "IsValue": True, "Unit": "mA", "BitField": {}},
        "0x0B": {"Function": "AverageCurrent()", "FunctionType": 12, "Access": 1, "IsValue": True, "Unit": "mA", "BitField": {}},
        "0x0C": {"Function": "MaxError()", "FunctionType": 13, "Access": 1, "IsValue": True, "Unit": "%", "BitField": {}},
        "0x0D": {"Function": "RelativeStateOfCharge()", "FunctionType": 14, "Access": 1, "IsValue": True, "Unit": "%", "BitField": {}},
        "0x0E": {"Function": "AbsoluteStateOfCharge()", "FunctionType": 15, "Access": 1, "IsValue": True, "Unit": "%", "BitField": {}},
        "0x0F": {"Function": "RemainingCapacity()", "FunctionType": 16, "Access": 1, "IsValue": True, "Unit": "mAh or 10mWh", "BitField": {}},
        "0x10": {"Function": "FullChargeCapacity()", "FunctionType": 17, "Access": 1, "IsValue": True, "Unit": "mAh or 10mWh", "BitField": {}},
        "0x11": {"Function": "RunTimeToEmpty()", "FunctionType": 18, "Access": 1, "IsValue": True, "Unit": "min", "BitField": {}},
        "0x12": {"Function": "AverageTimeToEmpty()", "FunctionType": 19, "Access": 1, "IsValue": True, "Unit": "min", "BitField": {}},
        "0x13": {"Function": "AverageTimeToFull()", "FunctionType": 20, "Access": 1, "IsValue": True, "Unit": "min", "BitField": {}},
        "0x14": {"Function": "ChargingCurrent()", "FunctionType": 21, "Access": 1, "IsValue": True, "Unit": "mA", "BitField": {}},
        "0x15": {"Function": "ChargingVoltage()", "FunctionType": 22, "Access": 1, "IsValue": True, "Unit": "mV", "BitField": {}},
        "0x16": {"Function": "BatteryStatus()", "FunctionType": 23, "Access": 1, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0x17": {"Function": "CycleCount()", "FunctionType": 24, "Access": 1, "IsValue": True, "Unit": "cycle", "BitField": {}},
        "0x18": {"Function": "DesignCapacity()", "FunctionType": 25, "Access": 1, "IsValue": True, "Unit": "mAh or 10mWh", "BitField": {}},
        "0x19": {"Function": "DesignVoltage()", "FunctionType": 26, "Access": 1, "IsValue": True, "Unit": "mV", "BitField": {}},
        "0x1A": {"Function": "SpecificationInfo()", "FunctionType": 27, "Access": 1, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0x1B": {"Function": "ManufactureDate()", "FunctionType": 28, "Access": 1, "IsValue": True, "Unit": "days", "BitField": {}},
        "0x1C": {"Function": "SerialNumber()", "FunctionType": 29, "Access": 1, "IsValue": True, "Unit": "NA", "BitField": {}},
        "0x20": {"Function": "ManufacturerName()", "FunctionType": 30, "Access": 1, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0x21": {"Function": "DeviceName()", "FunctionType": 31, "Access": 1, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0x22": {"Function": "DeviceChemistry()", "FunctionType": 32, "Access": 1, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0x23": {"Function": "ManufacturerData()", "FunctionType": 33, "Access": 1, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0xFE": {"Function": "Reserved", "FunctionType": 0, "Access": 0, "IsValue": False, "Unit": "NA", "BitField": {}},
        "0xFF": {"Function": "Reserved", "FunctionType": 0, "Access": 0, "IsValue": False, "Unit": "NA", "BitField": {}}
    }
}


def create_default_config() -> SbsConfig:
    """Build the default config (all command codes 0x00-0xFF, in order)."""
    body: Dict[str, SbsCommandDef] = {}
    for i in range(256):
        cc = f"0x{i:02X}"
        d = DEFAULT_SBS_CONFIG_DATA['Body'].get(cc, {
            "Function": "Reserved",
            "FunctionType": 0,
            "Access": 0,
            "IsValue": False,
            "Unit": "NA",
            "BitField": {},
        })
        body[cc] = _command_def_from_dict(d)

    return SbsConfig(title=DEFAULT_SBS_CONFIG_DATA['Title'], body=body, path=None)

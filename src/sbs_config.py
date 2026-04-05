from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

# IMPORTANT (English):
#   Use int keys, not string keys, to keep Combobox indices consistent.
FUNCTION_TYPE = {0: 'Customize', 1: 'ManufacturerAccess()', 2: 'RemainingCapacityAlarm()', 3: 'RemainingTimeAlarm()', 4: 'BatteryMode()', 5: 'AtRate()', 6: 'AtRateTimeToFull()', 7: 'AtRateTimeToEmpty()', 8: 'AtRateOK()', 9: 'Temperature()', 10: 'Voltage()', 11: 'Current()', 12: 'AverageCurrent()', 13: 'MaxError()', 14: 'RelativeStateOfCharge()', 15: 'AbsoluteStateOfCharge()', 16: 'RemainingCapacity()', 17: 'FullChargeCapacity()', 18: 'RunTimeToEmpty()', 19: 'AverageTimeToEmpty()', 20: 'AverageTimeToFull()', 21: 'ChargingCurrent()', 22: 'ChargingVoltage()', 23: 'BatteryStatus()', 24: 'CycleCount()', 25: 'DesignCapacity()', 26: 'DesignVoltage()', 27: 'SpecificationInfo()', 28: 'ManufactureDate()', 29: 'SerialNumber()', 30: 'ManufacturerName()', 31: 'DeviceName()', 32: 'DeviceChemistry()', 33: 'ManufacturerData()'}

ACCESS_TYPE = {0: 'NA', 1: 'R', 2: 'W', 3: 'RW'}


@dataclass
class SbsCommandDef:
    function: str
    function_type: int
    access: int
    is_value: bool
    unit: str
    bitfield: Dict[str, str]


@dataclass
class SbsConfig:
    title: str
    body: Dict[str, SbsCommandDef]
    path: Optional[Path] = None


class SbsConfigError(Exception):
    pass


def canonical_command_code(cc: str) -> str:
    cc = cc.strip()
    if cc.lower().startswith('0x'):
        cc = cc[2:]
    val = int(cc, 16)
    return f"0x{val:02X}"


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


def load_config(path: str | Path) -> SbsConfig:
    p = Path(path)
    with p.open('r', encoding='utf-8') as f:
        obj = json.load(f)

    validate_config_schema(obj)

    body: Dict[str, SbsCommandDef] = {}
    for cc_raw, d in obj['Body'].items():
        cc = canonical_command_code(cc_raw)
        ft = int(d['FunctionType'])
        fn = str(d['Function'])
        if ft != 0:
            fn = FUNCTION_TYPE.get(ft, fn)

        bitfield = dict(d['BitField']) if isinstance(d['BitField'], dict) else {}

        body[cc] = SbsCommandDef(
            function=fn,
            function_type=ft,
            access=int(d['Access']),
            is_value=bool(d['IsValue']),
            unit=str(d['Unit']),
            bitfield=bitfield,
        )

    return SbsConfig(title=obj['Title'], body=body, path=p)


def save_config(cfg: SbsConfig, path: str | Path) -> None:
    p = Path(path)
    obj = {'Title': cfg.title, 'Body': {}}

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

# Default SBS configuration embedded in code
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
    """Create a default SBS configuration from embedded data, including all command codes from 0x00 to 0xFF in order."""
    # Create body_data in order from 0x00 to 0xFF
    body_data = {}
    for i in range(256):
        cc = f"0x{i:02X}"
        if cc in DEFAULT_SBS_CONFIG_DATA['Body']:
            body_data[cc] = DEFAULT_SBS_CONFIG_DATA['Body'][cc]
        else:
            body_data[cc] = {
                "Function": "Reserved",
                "FunctionType": 0,
                "Access": 0,
                "IsValue": False,
                "Unit": "NA",
                "BitField": {}
            }

    # Now process the body_data as before
    body: Dict[str, SbsCommandDef] = {}
    for cc_raw, d in body_data.items():
        cc = canonical_command_code(cc_raw)
        ft = int(d['FunctionType'])
        fn = str(d['Function'])
        if ft != 0:
            fn = FUNCTION_TYPE.get(ft, fn)

        bitfield = dict(d['BitField']) if isinstance(d['BitField'], dict) else {}

        body[cc] = SbsCommandDef(
            function=fn,
            function_type=ft,
            access=int(d['Access']),
            is_value=bool(d['IsValue']),
            unit=str(d['Unit']),
            bitfield=bitfield,
        )

    return SbsConfig(title=DEFAULT_SBS_CONFIG_DATA['Title'], body=body, path=None)
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

FUNCTION_TYPE = {
    0: 'Customize',
    1: 'ManufacturerAccess()',
    2: 'RemainingCapacityAlarm()',
    3: 'RemainingTimeAlarm()',
    4: 'BatteryMode()',
    5: 'AtRate()',
    6: 'AtRateTimeToFull()',
    7: 'AtRateTimeToEmpty()',
    8: 'AtRateOK()',
    9: 'Temperature()',
    10: 'Voltage()',
    11: 'Current()',
    12: 'AverageCurrent()',
    13: 'MaxError()',
    14: 'RelativeStateOfCharge()',
    15: 'AbsoluteStateOfCharge()',
    16: 'RemainingCapacity()',
    17: 'FullChargeCapacity()',
    18: 'RunTimeToEmpty()',
    19: 'AverageTimeToEmpty()',
    20: 'AverageTimeToFull()',
    21: 'ChargingCurrent()',
    22: 'ChargingVoltage()',
    23: 'BatteryStatus()',
    24: 'CycleCount()',
    25: 'DesignCapacity()',
    26: 'DesignVoltage()',
    27: 'SpecificationInfo()',
    28: 'ManufactureDate()',
    29: 'SerialNumber()',
    30: 'ManufacturerName()',
    31: 'DeviceName()',
    32: 'DeviceChemistry()',
    33: 'ManufacturerData()',
}

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


def validate_config_schema(obj: Dict[str, Any]) -> None:
    """Validate JSON schema quickly.

    Raises:
        SbsConfigError: if schema is invalid.
    """
    if not isinstance(obj, dict):
        raise SbsConfigError('Config root must be an object.')
    if 'Title' not in obj or 'Body' not in obj:
        raise SbsConfigError('Config must contain Title and Body.')
    if not isinstance(obj['Title'], str):
        raise SbsConfigError('Title must be a string.')
    if not isinstance(obj['Body'], dict):
        raise SbsConfigError('Body must be an object.')

    for cc, d in obj['Body'].items():
        if not isinstance(cc, str) or not cc.startswith('0x'):
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
    for cc, d in obj['Body'].items():
        ft = int(d['FunctionType'])
        fn = str(d['Function'])
        # If FunctionType is not 0, force function string from enumeration
        if ft != 0:
            fn = FUNCTION_TYPE.get(ft, fn)

        body[cc.upper()] = SbsCommandDef(
            function=fn,
            function_type=ft,
            access=int(d['Access']),
            is_value=bool(d['IsValue']),
            unit=str(d['Unit']),
            bitfield=dict(d['BitField']) if isinstance(d['BitField'], dict) else {},
        )

    return SbsConfig(title=obj['Title'], body=body, path=p)


def save_config(cfg: SbsConfig, path: str | Path) -> None:
    p = Path(path)
    obj = {'Title': cfg.title, 'Body': {}}
    for cc, d in cfg.body.items():
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

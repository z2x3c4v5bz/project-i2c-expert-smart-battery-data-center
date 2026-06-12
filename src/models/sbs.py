from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

# IMPORTANT: Use int keys, not string keys, to keep Combobox indices consistent.
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

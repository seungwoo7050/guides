from __future__ import annotations

from enum import Enum


class Type(Enum):
    INT = "Int"
    BOOL = "Bool"
    STRING = "String"
    UNIT = "Unit"
    ERROR = "<error>"

from enum import Enum


class UppercaseStrEnum(Enum):
    def __init__(self, value):
        self._value_ = value.upper()


class devEnvs(UppercaseStrEnum):
    DEV = "DEV"
    TEST = "TEST"
    PROD = "PROD"

from enum import Enum

# pydantic v2
# from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseSettings


class UppercaseStrEnum(Enum):
    def __init__(self, value):
        self._value_ = value.upper()


class devEnvs(UppercaseStrEnum):
    DEV = "DEV"
    TEST = "TEST"
    PROD = "PROD"


class MyBaseSettings(BaseSettings):
    # Base
    api_v1_prefix: str
    debug: bool
    project_name: str
    version: str
    description: str
    data_dir: str

    # model_config = SettingsConfigDict(env_file=".env")

    # neccesary to support lru_cache in fastapi dependency injection
    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))

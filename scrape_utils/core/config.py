import os
from enum import Enum
from typing import Final

# pydantic v2
# from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseSettings, Field, SecretStr
from pydantic_vault import vault_config_settings_source

PYTHON_ENV: Final[str] = os.getenv("PYTHON_ENV", "").upper()
if not PYTHON_ENV:
    raise ValueError("PYTHON_ENV should be set")

VAULT_SECRET_PATH: Final[str] = "secret/data"


def env_fmt(key: str) -> str:
    return f"{VAULT_SECRET_PATH}/{key}/{PYTHON_ENV.lower()}"


BASE_SETTINGS_PATH: Final[str] = env_fmt("base_settings")
DATABASE_SETTINGS_PATH: Final[str] = env_fmt("db")
REDIS_SETTINGS_PATH: Final[str] = env_fmt("redis")


class UppercaseStrEnum(Enum):
    def __init__(self, value):
        self._value_ = value.upper()


class devEnvs(UppercaseStrEnum):
    DEV = "DEV"
    TEST = "TEST"
    PROD = "PROD"


class MyBaseSettings(BaseSettings):
    # Base
    api_v1_prefix: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="api_v1_prefix"
    )
    debug: bool = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="debug"
    )
    project_name: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="project_name"
    )
    version: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="version"
    )
    description: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="description"
    )
    data_dir: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="data_dir"
    )

    # model_config = SettingsConfigDict(env_file=".env")

    # neccesary to support lru_cache in fastapi dependency injection
    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))

    class Config:
        # vault_url: str = "https://vault.tld"
        # vault_url: str = os.environ["VAULT_ADDR"]
        vault_url: str
        vault_token: SecretStr
        # vault_token: SecretStr = os.environ["VAULT_TOKEN"]
        # Optional, pydantic-vault supports Vault namespaces (for Vault Enterprise)
        # vault_namespace: str = "your/namespace"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            # Choose the order of settings sources
            return (
                init_settings,
                env_settings,
                vault_config_settings_source,
                file_secret_settings,
            )


class DBSettings(BaseSettings):
    # Database
    db_host: str = Field(
        ..., vault_secret_path=DATABASE_SETTINGS_PATH, vault_secret_key="host"
    )
    db_port: int = Field(
        ..., vault_secret_path=DATABASE_SETTINGS_PATH, vault_secret_key="port"
    )
    db_pass: SecretStr = Field(
        ..., vault_secret_path=DATABASE_SETTINGS_PATH, vault_secret_key="pass"
    )
    db_name: str = Field(
        ..., vault_secret_path=DATABASE_SETTINGS_PATH, vault_secret_key="name"
    )
    db_connection_str: SecretStr = Field(
        ..., vault_secret_path=DATABASE_SETTINGS_PATH, vault_secret_key="connection_str"
    )
    db_async_connection_str: SecretStr = Field(
        ...,
        vault_secret_path=DATABASE_SETTINGS_PATH,
        vault_secret_key="async_connection_str",
    )
    # db_exclude_tables: List[str]

    # class Config(MyBaseSettings.Config):
    #     pass


class ScrapeSettings(MyBaseSettings, DBSettings):
    # Redis
    redis_host: str = Field(
        ..., vault_secret_path=REDIS_SETTINGS_PATH, vault_secret_key="host"
    )
    redis_port: int = Field(
        ..., vault_secret_path=REDIS_SETTINGS_PATH, vault_secret_key="port"
    )
    redis_db: int = Field(
        ..., vault_secret_path=REDIS_SETTINGS_PATH, vault_secret_key="db"
    )
    redis_url: str = Field(
        ..., vault_secret_path=REDIS_SETTINGS_PATH, vault_secret_key="url"
    )

    # list
    redis_start_urls_key: str = Field(
        ..., vault_secret_path=REDIS_SETTINGS_PATH, vault_secret_key="start_urls_key"
    )
    # list
    redis_items_key: str = Field(
        ..., vault_secret_path=REDIS_SETTINGS_PATH, vault_secret_key="items_key"
    )
    # set
    redis_verify_scraped_key: str = Field(
        ...,
        vault_secret_path=REDIS_SETTINGS_PATH,
        vault_secret_key="verify_scraped_key",
    )

    class Config(MyBaseSettings.Config):
        pass


class APISettings(MyBaseSettings, DBSettings):
    # RabbitMQ
    rmq_host: str
    rmq_port: int
    rmq_user: str
    rmq_password: str
    rmq_url: str

    rmq_publish_queue: str
    rmq_consume_queue: str
    rmq_add_row_queue: str
    rmq_verify_scraped_queue: str

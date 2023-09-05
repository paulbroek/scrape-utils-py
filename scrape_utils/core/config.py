import logging
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

# vault dev mode uses secret/data path
# VAULT_SECRET_PATH: Final[str] = "secret/data"
VAULT_SECRET_PATH: Final[str] = "secret"


def env_fmt(key: str) -> str:
    return f"{VAULT_SECRET_PATH}/{key}/{PYTHON_ENV.lower()}"


BASE_SETTINGS_PATH: Final[str] = env_fmt("base_settings")
DB_SETTINGS_PATH: Final[str] = env_fmt("db")
REDIS_SETTINGS_PATH: Final[str] = env_fmt("redis")
RMQ_SETTINGS_PATH: Final[str] = env_fmt("rmq")

logger = logging.getLogger(__name__)


class UppercaseStrEnum(Enum):
    def __init__(self, value):
        self._value_ = value.upper()


class devEnvs(UppercaseStrEnum):
    DEV = "DEV"
    TEST = "TEST"
    PROD = "PROD"


# class MyBaseSettings(BaseSettings, metaclass=MyMetaclass):
class MyBaseSettings(BaseSettings):
    # neccesary to support lru_cache in fastapi dependency injection
    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))

    @classmethod
    def create_with_customizations(cls, custom_path: str):
        """All fields can get a project name prefix.

        So that multiple package keys can be retrieved
        A fix/replacement for vault namespaces
        """
        assert not custom_path.endswith("/"), "please pass a plain string"
        # custom_path = os.getenv("VAULT_KEY_PREFIX")
        # instance = cls()
        if custom_path:
            for field_name, field_value in cls.__fields__.items():
                field_info = field_value.field_info
                field_info.extra["vault_secret_path"] = field_info.extra[
                    "vault_secret_path"
                ].replace(
                    VAULT_SECRET_PATH + "/", f"{VAULT_SECRET_PATH}/{custom_path}/"
                )
                cls.__fields__[field_name].field_info = field_info

            instance = cls()
        return instance


class GeneralSettings(MyBaseSettings):
    # Base
    base_settings_api_v1_prefix: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="api_v1_prefix"
    )
    base_settings_debug: bool = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="debug"
    )
    base_settings_project_name: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="project_name"
    )
    base_settings_version: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="version"
    )
    base_settings_description: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="description"
    )
    base_settings_data_dir: str = Field(
        ..., vault_secret_path=BASE_SETTINGS_PATH, vault_secret_key="data_dir"
    )

    # model_config = SettingsConfigDict(env_file=".env")

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
                file_secret_settings,
                vault_config_settings_source,
            )


class DBSettings(MyBaseSettings):
    # Database
    db_host: str = Field(
        ..., vault_secret_path=DB_SETTINGS_PATH, vault_secret_key="host"
    )
    db_port: int = Field(
        ..., vault_secret_path=DB_SETTINGS_PATH, vault_secret_key="port"
    )
    db_pass: SecretStr = Field(
        ..., vault_secret_path=DB_SETTINGS_PATH, vault_secret_key="pass"
    )
    db_name: str = Field(
        ..., vault_secret_path=DB_SETTINGS_PATH, vault_secret_key="name"
    )
    db_connection_str: SecretStr = Field(
        ..., vault_secret_path=DB_SETTINGS_PATH, vault_secret_key="connection_str"
    )
    db_async_connection_str: SecretStr = Field(
        ...,
        vault_secret_path=DB_SETTINGS_PATH,
        vault_secret_key="async_connection_str",
    )
    # db_exclude_tables: List[str]

    # class Config(MyBaseSettings.Config):
    #     pass


class ScrapeSettings(GeneralSettings, DBSettings):
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

    class Config(GeneralSettings.Config):
        pass


class APISettings(GeneralSettings, DBSettings):
    # RabbitMQ
    rmq_host: str = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="host",
    )

    rmq_port: int = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="port",
    )

    rmq_user: str = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="user",
    )

    rmq_password: str = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="password",
    )

    rmq_url: str = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="url",
    )

    rmq_publish_queue: str = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="publish_queue",
    )

    rmq_consume_queue: str = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="consume_queue",
    )

    rmq_add_row_queue: str = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="add_row_queue",
    )

    rmq_verify_scraped_queue: str = Field(
        ...,
        vault_secret_path=RMQ_SETTINGS_PATH,
        vault_secret_key="verify_scraped_queue",
    )

    class Config(GeneralSettings.Config):
        pass

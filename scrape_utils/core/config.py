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


class DBSettings(BaseSettings):
    # Database
    db_host: str
    db_port: int
    db_pass: str
    db_name: str
    db_connection_str: str
    db_async_connection_str: str
    # db_exclude_tables: List[str]


class ScrapeSettings(MyBaseSettings, DBSettings):
    # Redis
    redis_host: str
    redis_port: int
    redis_db: int
    redis_url: str

    redis_start_urls_key: str  # list
    redis_items_key: str  # list
    redis_verify_scraped_key: str  # set


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

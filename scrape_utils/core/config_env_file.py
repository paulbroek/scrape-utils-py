"""config_env_file.py.

Load the right env file
"""
import logging
from os import getenv
from pathlib import Path
from sys import modules
from typing import Final, Tuple

from rarc_utils.log import get_create_logger

from .config import devEnvs
from .settings import ENV_FILE_PATTERN

logger = get_create_logger(cmdLevel=logging.INFO, color=1)


def log_python_env(devEnv: devEnvs) -> None:
    """Log what python_env is set."""
    msg: str = f"running in {devEnv.name} mode"

    if devEnv == devEnvs.PROD:
        logger.warning(msg)
    else:
        logger.info(msg)


def config_env(override_pytest: bool = False) -> Tuple[devEnvs, Path]:
    PYTHON_ENV_STR: Final[str] = getenv("PYTHON_ENV", "").upper()
    if not PYTHON_ENV_STR:
        raise ValueError("PYTHON_ENV should be set")

    if PYTHON_ENV_STR not in dict(devEnvs.__members__):
        raise ValueError(f"{PYTHON_ENV_STR=} not in {list(devEnvs.__members__.keys())}")

    PYTHON_ENV: devEnvs = devEnvs[PYTHON_ENV_STR]

    # even in PROD, always use TEST when pytest is present
    if "pytest" in modules and not override_pytest:
        logger.info(
            f"requested {PYTHON_ENV.name} env, but `pytest` is in modules, so using TEST env"
        )
        PYTHON_ENV = devEnvs.TEST

    ENV_DIR: Final[str] = getenv("ENV_DIR", "")
    if not ENV_DIR:
        raise ValueError("ENV_DIR should be set")

    ENV_FILE_PATH: Final[Path] = Path(ENV_DIR)
    if not ENV_FILE_PATH.exists():
        raise FileNotFoundError(f"{ENV_FILE_PATH=} not found")

    # this .env file will be used in module
    ENV_FILE_NAME: Final[str] = ENV_FILE_PATTERN.format(PYTHON_ENV.name.lower())
    ENV_FILE: Final[Path] = ENV_FILE_PATH / ENV_FILE_NAME

    if not ENV_FILE.exists():
        raise FileNotFoundError(f"{ENV_FILE=} not found")

    log_python_env(PYTHON_ENV)

    return PYTHON_ENV, ENV_FILE


PYTHON_ENV, ENV_FILE = config_env()

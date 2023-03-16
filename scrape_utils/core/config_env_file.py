"""config_env_file.py.

Load the right env file
"""
import logging
from os import getenv
from pathlib import Path
from sys import modules
from typing import Final, Optional, Tuple

from rarc_utils.log import get_create_logger

from .config import devEnvs
from .settings import ENV_FILE_PATTERN

logger = get_create_logger(cmdLevel=logging.INFO, color=1)


def log_python_env(devEnv: devEnvs, env_file: Path) -> None:
    """Log what python_env is set."""
    msg: str = (
        f"running in {devEnv.name} mode. config loaded from: {env_file.as_posix()}"
    )

    if devEnv == devEnvs.PROD:
        logger.warning(msg)
    else:
        logger.info(msg)


def config_env(
    env_dir_override: Optional[str] = None, override_pytest: bool = False
) -> Tuple[devEnvs, Path]:
    """Configure the environment fils to load for set PYTHON_ENV."""
    python_env_str: Final[str] = getenv("PYTHON_ENV", "").upper()
    if not python_env_str:
        raise ValueError("PYTHON_ENV should be set")

    if python_env_str not in dict(devEnvs.__members__):
        raise ValueError(f"{python_env_str=} not in {list(devEnvs.__members__.keys())}")

    python_env: devEnvs = devEnvs[python_env_str]

    # even in PROD, always use TEST when pytest is present
    if "pytest" in modules and not override_pytest:
        logger.info(
            f"requested {python_env.name} env, but `pytest` is in modules, so using TEST env"
        )
        python_env = devEnvs.TEST

    env_dir: Final[str] = getenv("ENV_DIR", "")
    if not env_dir:
        raise ValueError("ENV_DIR should be set")

    env_file_path: Final[Path] = (
        Path(env_dir_override) if env_dir_override is not None else Path(env_dir)
    )
    if not env_file_path.exists():
        raise FileNotFoundError(f"{env_file_path=} not found")

    # this .env file will be used in module
    env_file_name: Final[str] = ENV_FILE_PATTERN.format(python_env.name.lower())
    env_file: Final[Path] = env_file_path / env_file_name

    if not env_file.exists():
        raise FileNotFoundError(f"{env_file=} not found")

    log_python_env(python_env, env_file)

    return python_env, env_file


PYTHON_ENV, ENV_FILE = config_env()

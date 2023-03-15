from typing import Final

DECODE_RESPONSES: Final[bool] = True
MAX_REDIS_CONNECTIONS_DEFAULT: Final[int] = 100
START_URLS_KEY: Final[str] = "rspider:start_urls"

REDIS_SITEMAP_KEY_FORMAT: Final[str] = "sitemap-{collection}"

PG_POOL_SIZE_DEFAULT: Final[int] = 10

ENV_FILE_PATTERN: Final[str] = ".env.{}"

REQUIRED_SOFT_ULIMIT: Final[int] = 10_000

MODULE_DIR_FORMAT: Final[
    str
] = "/home/paul/repos/misc-scraping/misc_scraping/{module_name}/config"

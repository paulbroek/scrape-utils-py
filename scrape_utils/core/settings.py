from typing import Final

# TODO: or move to settings model?
DECODE_RESPONSES: Final[bool] = True
MAX_REDIS_CONNECTIONS: Final[int] = 100
START_URLS_KEY: Final[str] = "rspider:start_urls"

REDIS_SITEMAP_KEY_FORMAT: Final[str] = "sitemap-{collection}"

PG_POOL_SIZE: Final[int] = 40

ENV_FILE_PATTERN: Final[str] = ".env.{}"

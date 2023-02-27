import logging

from scrape_utils.core.crud import ScrapeItemCRUD
from sqlmodel.ext.asyncio.session import AsyncSession

from . import HttpCacheItem

logger = logging.getLogger(__name__)


class CacheCRUD(ScrapeItemCRUD):
    model = HttpCacheItem  # Replace `HttpCacheItem` with the actual model class

    def __init__(self, session: AsyncSession):
        super().__init__(session)

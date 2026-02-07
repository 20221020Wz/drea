"""零售商数据采集模块"""

from .base import Product as ProductData, RetailerScraper
from .homedepot import HomeDepotScraper
from .walmart import WalmartScraper
from .lowes import LowesScraper
from .harborfreight import HarborFreightScraper

SCRAPER_REGISTRY: dict[str, type[RetailerScraper]] = {
    "homedepot": HomeDepotScraper,
    "walmart": WalmartScraper,
    "lowes": LowesScraper,
    "harborfreight": HarborFreightScraper,
}


def get_scraper(retailer: str) -> RetailerScraper:
    """根据零售商名称获取对应的爬虫实例"""
    scraper_cls = SCRAPER_REGISTRY.get(retailer)
    if not scraper_cls:
        raise ValueError(
            f"未知的零售商: {retailer}. 支持: {list(SCRAPER_REGISTRY.keys())}"
        )
    return scraper_cls()


__all__ = [
    "ProductData",
    "RetailerScraper",
    "HomeDepotScraper",
    "WalmartScraper",
    "LowesScraper",
    "HarborFreightScraper",
    "SCRAPER_REGISTRY",
    "get_scraper",
]

"""爬虫基类 - 零售商适配器模式"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx
from fake_useragent import UserAgent
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class Product:
    """标准化产品数据结构"""

    sku: str
    name: str
    brand: str
    price: float
    rating: Optional[float]
    review_count: int
    description: str
    specs: dict = field(default_factory=dict)
    image_urls: list[str] = field(default_factory=list)
    product_url: str = ""
    retailer: str = ""
    in_store_only: bool = False
    category: str = ""
    model_number: str = ""

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "rating": self.rating,
            "review_count": self.review_count,
            "description": self.description,
            "specs": self.specs,
            "image_urls": self.image_urls,
            "product_url": self.product_url,
            "retailer": self.retailer,
            "in_store_only": self.in_store_only,
            "category": self.category,
            "model_number": self.model_number,
        }


class RetailerScraper(ABC):
    """零售商爬虫基类

    所有零售商适配器继承此类，实现统一的搜索和产品详情获取接口。
    内置反爬策略：请求间隔随机化、User-Agent轮换、失败重试。
    """

    RETAILER_NAME: str = ""
    BASE_URL: str = ""

    def __init__(self):
        self.ua = UserAgent()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def _get_browser(self) -> Browser:
        """获取或创建浏览器实例"""
        if self._browser is None or not self._browser.is_connected():
            pw = await async_playwright().start()
            launch_args = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            }
            if settings.proxy_config:
                launch_args["proxy"] = settings.proxy_config
            self._browser = await pw.chromium.launch(**launch_args)
        return self._browser

    async def _new_context(self) -> BrowserContext:
        """创建新的浏览器上下文（独立的cookie和缓存）"""
        browser = await self._get_browser()
        context = await browser.new_context(
            user_agent=self.ua.random,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )
        # 添加反自动化检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        return context

    async def _random_delay(self):
        """随机延迟，模拟人工操作"""
        delay = random.uniform(settings.scrape_delay_min, settings.scrape_delay_max)
        await asyncio.sleep(delay)

    async def _safe_goto(self, page: Page, url: str, wait_until: str = "domcontentloaded"):
        """安全的页面导航，带超时和重试"""
        try:
            await page.goto(url, wait_until=wait_until, timeout=settings.scrape_timeout)
        except Exception as e:
            logger.warning(f"页面加载超时或失败: {url}, 错误: {e}")
            raise

    async def _scroll_to_bottom(self, page: Page, max_scrolls: int = 10):
        """模拟滚动到页面底部，触发懒加载"""
        for _ in range(max_scrolls):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.5)

    @abstractmethod
    async def search(
        self,
        keyword: str,
        in_store_only: bool = True,
        max_pages: int = 10,
    ) -> list[Product]:
        """搜索产品

        Args:
            keyword: 搜索关键词
            in_store_only: 是否仅筛选店内销售
            max_pages: 最大翻页数

        Returns:
            产品列表
        """
        pass

    @abstractmethod
    async def get_product_detail(self, url: str) -> Optional[Product]:
        """获取单个产品详情

        Args:
            url: 产品页面URL

        Returns:
            产品数据，获取失败返回None
        """
        pass

    async def search_multiple_keywords(
        self,
        keywords: list[str],
        in_store_only: bool = True,
        max_pages: int = 10,
    ) -> list[Product]:
        """搜索多个关键词并去重

        Args:
            keywords: 关键词列表
            in_store_only: 是否仅筛选店内销售
            max_pages: 每个关键词的最大翻页数

        Returns:
            去重后的产品列表
        """
        seen_skus: set[str] = set()
        all_products: list[Product] = []

        for keyword in keywords:
            logger.info(f"[{self.RETAILER_NAME}] 搜索关键词: {keyword}")
            try:
                products = await self.search(
                    keyword, in_store_only=in_store_only, max_pages=max_pages
                )
                for product in products:
                    if product.sku not in seen_skus:
                        seen_skus.add(product.sku)
                        all_products.append(product)
                logger.info(
                    f"[{self.RETAILER_NAME}] 关键词 '{keyword}' 找到 {len(products)} 个产品, "
                    f"新增 {len(products) - len([p for p in products if p.sku in seen_skus])} 个"
                )
            except Exception as e:
                logger.error(f"[{self.RETAILER_NAME}] 搜索 '{keyword}' 失败: {e}")
                continue

            await self._random_delay()

        logger.info(f"[{self.RETAILER_NAME}] 总计获取 {len(all_products)} 个唯一产品")
        return all_products

    async def download_image(self, url: str, sku: str) -> Optional[str]:
        """下载产品图片到本地

        Args:
            url: 图片URL
            sku: 产品SKU，用于文件命名

        Returns:
            本地文件路径，失败返回None
        """
        try:
            retailer_dir = settings.image_dir / self.RETAILER_NAME
            retailer_dir.mkdir(parents=True, exist_ok=True)

            ext = url.rsplit(".", 1)[-1].split("?")[0] if "." in url else "jpg"
            if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
                ext = "jpg"
            filename = f"{sku}.{ext}"
            filepath = retailer_dir / filename

            if filepath.exists():
                return str(filepath)

            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=15, follow_redirects=True)
                resp.raise_for_status()
                filepath.write_bytes(resp.content)

            logger.debug(f"图片已下载: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.warning(f"图片下载失败: {url}, 错误: {e}")
            return None

    async def close(self):
        """清理浏览器资源"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
            self._browser = None

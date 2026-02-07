"""Walmart 适配器"""

import logging
import re
from typing import Optional
from urllib.parse import quote_plus, urlencode

from playwright.async_api import Page

from .base import Product, RetailerScraper

logger = logging.getLogger(__name__)


class WalmartScraper(RetailerScraper):
    """Walmart 产品数据爬虫

    支持功能：
    - 关键词搜索，可筛选 In-Store Only
    - 自动翻页采集
    - 产品详情页规格提取
    """

    RETAILER_NAME = "walmart"
    BASE_URL = "https://www.walmart.com"

    def _build_search_url(self, keyword: str, in_store_only: bool, page: int = 1) -> str:
        """构建搜索URL"""
        encoded = quote_plus(keyword)
        url = f"{self.BASE_URL}/search"
        params = {"q": encoded}
        if in_store_only:
            params["facet"] = "fulfillment_method_in_store:In-store"
        if page > 1:
            params["page"] = str(page)
        return url + "?" + urlencode(params)

    async def _parse_search_results(self, page: Page) -> list[dict]:
        """解析搜索结果"""
        items = []
        try:
            await page.wait_for_selector(
                '[data-testid="list-view"] [data-item-id], '
                '.search-result-gridview-item',
                timeout=15000,
            )
            await self._scroll_to_bottom(page, max_scrolls=5)

            cards = await page.query_selector_all(
                '[data-testid="list-view"] [data-item-id], '
                '.search-result-gridview-item'
            )

            for card in cards:
                try:
                    item = {}

                    # 产品ID
                    item_id = await card.get_attribute("data-item-id")
                    if item_id:
                        item["sku"] = item_id

                    # 产品链接和名称
                    link_el = await card.query_selector(
                        'a[link-identifier="itemName"], '
                        'a[data-testid="product-title"]'
                    )
                    if link_el:
                        href = await link_el.get_attribute("href")
                        item["product_url"] = (
                            f"{self.BASE_URL}{href}" if href and not href.startswith("http")
                            else href or ""
                        )
                        title_span = await link_el.query_selector("span")
                        if title_span:
                            item["name"] = (await title_span.inner_text()).strip()
                        else:
                            item["name"] = (await link_el.inner_text()).strip()

                    # 价格
                    price_el = await card.query_selector(
                        '[data-automation-id="product-price"] .f2, '
                        '[itemprop="price"], '
                        '.price-main .visuallyhidden'
                    )
                    if price_el:
                        price_text = await price_el.inner_text()
                        price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                        if price_match:
                            item["price"] = float(price_match.group())

                    # 评分
                    rating_el = await card.query_selector(
                        '[data-testid="product-ratings"] .w_iUH7, '
                        '.stars-reviews-count'
                    )
                    if rating_el:
                        rating_text = await rating_el.get_attribute("aria-label") or ""
                        if not rating_text:
                            rating_text = await rating_el.inner_text()
                        rating_match = re.search(r"([\d.]+)\s*out of", rating_text)
                        if rating_match:
                            item["rating"] = float(rating_match.group(1))

                    # 评论数
                    review_el = await card.query_selector(
                        '[data-testid="product-ratings"] .sans-serif, '
                        '.stars-reviews-count-node'
                    )
                    if review_el:
                        review_text = await review_el.inner_text()
                        review_match = re.search(r"([\d,]+)", review_text)
                        if review_match:
                            item["review_count"] = int(
                                review_match.group(1).replace(",", "")
                            )

                    # 品牌 (通常在产品名称中)
                    item["brand"] = self._extract_brand_from_name(item.get("name", ""))

                    # 图片
                    img_el = await card.query_selector("img[data-testid]")
                    if not img_el:
                        img_el = await card.query_selector("img")
                    if img_el:
                        src = await img_el.get_attribute("src")
                        if src:
                            item["image_url"] = src

                    # 配送标记
                    fulfillment_el = await card.query_selector(
                        '[data-testid="fulfillment-badge"]'
                    )
                    if fulfillment_el:
                        text = await fulfillment_el.inner_text()
                        item["in_store_only"] = (
                            "pickup" in text.lower() and "shipping" not in text.lower()
                        )

                    if item.get("name"):
                        if not item.get("sku"):
                            url = item.get("product_url", "")
                            sku_match = re.search(r"/(\d+)(?:\?|$)", url)
                            if sku_match:
                                item["sku"] = sku_match.group(1)
                        if item.get("sku"):
                            items.append(item)

                except Exception as e:
                    logger.debug(f"解析Walmart产品卡片失败: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Walmart搜索结果解析失败: {e}")

        return items

    @staticmethod
    def _extract_brand_from_name(name: str) -> str:
        """从产品名称中提取品牌（Walmart产品名通常以品牌开头）"""
        known_brands = [
            "CRAFTSMAN", "Craftsman", "DEWALT", "DeWalt", "Milwaukee",
            "IRWIN", "Irwin", "Stanley", "STANLEY", "Channellock",
            "CHANNELLOCK", "Knipex", "KNIPEX", "Crescent", "CRESCENT",
            "Klein Tools", "KLEIN", "Kobalt", "KOBALT", "Husky",
            "TEKTON", "Tekton", "WORKPRO", "Workpro", "GEARWRENCH",
            "GearWrench", "Vise-Grip", "VISE-GRIP", "Pittsburgh",
            "Snap-on", "SNAP-ON", "Wiha", "WIHA", "Wera",
        ]
        for brand in known_brands:
            if name.lower().startswith(brand.lower()):
                return brand
        # 默认取第一个单词
        parts = name.split()
        return parts[0] if parts else ""

    async def _has_next_page(self, page: Page) -> bool:
        """检查是否有下一页"""
        next_btn = await page.query_selector(
            'a[data-testid="NextPage"], '
            'nav[aria-label="pagination"] a:last-child:not([aria-disabled="true"])'
        )
        return next_btn is not None

    async def search(
        self,
        keyword: str,
        in_store_only: bool = True,
        max_pages: int = 10,
    ) -> list[Product]:
        """搜索Walmart产品"""
        products: list[Product] = []
        context = await self._new_context()

        try:
            page = await context.new_page()
            current_page = 1

            while current_page <= max_pages:
                url = self._build_search_url(keyword, in_store_only, current_page)
                logger.info(f"[Walmart] 抓取第 {current_page} 页: {url}")

                await self._safe_goto(page, url)
                await self._random_delay()

                items = await self._parse_search_results(page)
                if not items:
                    logger.info(f"[Walmart] 第 {current_page} 页无结果，停止翻页")
                    break

                for item in items:
                    products.append(
                        Product(
                            sku=item.get("sku", ""),
                            name=item.get("name", ""),
                            brand=item.get("brand", ""),
                            price=item.get("price", 0.0),
                            rating=item.get("rating"),
                            review_count=item.get("review_count", 0),
                            description="",
                            image_urls=[item["image_url"]] if item.get("image_url") else [],
                            product_url=item.get("product_url", ""),
                            retailer=self.RETAILER_NAME,
                            in_store_only=item.get("in_store_only", False),
                        )
                    )

                has_next = await self._has_next_page(page)
                if not has_next:
                    break

                current_page += 1
                await self._random_delay()

        except Exception as e:
            logger.error(f"[Walmart] 搜索失败: {e}")
        finally:
            await context.close()

        logger.info(f"[Walmart] 搜索 '{keyword}' 完成，共 {len(products)} 个产品")
        return products

    async def get_product_detail(self, url: str) -> Optional[Product]:
        """获取Walmart产品详情"""
        context = await self._new_context()

        try:
            page = await context.new_page()
            await self._safe_goto(page, url, wait_until="networkidle")
            await self._random_delay()

            product_data: dict = {"product_url": url, "retailer": self.RETAILER_NAME}

            # 产品名称
            title_el = await page.query_selector(
                'h1[itemprop="name"], [data-testid="product-title"]'
            )
            if title_el:
                product_data["name"] = (await title_el.inner_text()).strip()

            # 价格
            price_el = await page.query_selector(
                '[itemprop="price"], [data-testid="price-wrap"] .f1'
            )
            if price_el:
                price_text = await price_el.inner_text()
                price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                if price_match:
                    product_data["price"] = float(price_match.group())

            # 品牌
            brand_el = await page.query_selector(
                'a[link-identifier="brand"], [itemprop="brand"]'
            )
            if brand_el:
                product_data["brand"] = (await brand_el.inner_text()).strip()

            # 评分
            rating_el = await page.query_selector(
                '[itemprop="ratingValue"], .rating-number'
            )
            if rating_el:
                text = await rating_el.inner_text()
                match = re.search(r"[\d.]+", text)
                if match:
                    product_data["rating"] = float(match.group())

            # 评论数
            review_el = await page.query_selector('[itemprop="reviewCount"]')
            if review_el:
                text = await review_el.inner_text()
                match = re.search(r"[\d,]+", text)
                if match:
                    product_data["review_count"] = int(match.group().replace(",", ""))

            # 描述
            desc_el = await page.query_selector(
                '[data-testid="product-description"], .about-desc'
            )
            if desc_el:
                product_data["description"] = (await desc_el.inner_text()).strip()

            # 规格
            specs = {}
            spec_rows = await page.query_selector_all(
                '.specification-table tr, '
                '[data-testid="product-specifications"] tr'
            )
            for row in spec_rows:
                cells = await row.query_selector_all("td, th")
                if len(cells) >= 2:
                    key = (await cells[0].inner_text()).strip()
                    value = (await cells[1].inner_text()).strip()
                    if key and value:
                        specs[key] = value
            product_data["specs"] = specs

            # 图片
            image_urls = []
            img_els = await page.query_selector_all(
                '[data-testid="hero-image"] img, '
                '.prod-HeroImage img'
            )
            for img in img_els:
                src = await img.get_attribute("src")
                if src and "placeholder" not in src:
                    image_urls.append(src)
            product_data["image_urls"] = image_urls

            # SKU
            sku_match = re.search(r"/(\d+)(?:\?|$)", url)
            product_data["sku"] = sku_match.group(1) if sku_match else ""

            return Product(
                sku=product_data.get("sku", ""),
                name=product_data.get("name", ""),
                brand=product_data.get("brand", ""),
                price=product_data.get("price", 0.0),
                rating=product_data.get("rating"),
                review_count=product_data.get("review_count", 0),
                description=product_data.get("description", ""),
                specs=product_data.get("specs", {}),
                image_urls=product_data.get("image_urls", []),
                product_url=url,
                retailer=self.RETAILER_NAME,
            )

        except Exception as e:
            logger.error(f"[Walmart] 产品详情获取失败 {url}: {e}")
            return None
        finally:
            await context.close()

"""Harbor Freight 适配器"""

import logging
import re
from typing import Optional
from urllib.parse import quote_plus, urlencode

from playwright.async_api import Page

from .base import Product, RetailerScraper

logger = logging.getLogger(__name__)


class HarborFreightScraper(RetailerScraper):
    """Harbor Freight 产品数据爬虫

    Harbor Freight主要是自有品牌（Pittsburgh, Quinn, Doyle等），
    产品均为店内销售，无需额外筛选in-store-only。

    支持功能：
    - 关键词搜索
    - 自动翻页采集
    - 产品详情页规格提取
    """

    RETAILER_NAME = "harborfreight"
    BASE_URL = "https://www.harborfreight.com"

    # Harbor Freight自有品牌列表
    # Longer names first to match "Pittsburgh Pro" before "Pittsburgh"
    HF_BRANDS = [
        "Pittsburgh Pro", "Pittsburgh", "Quinn", "Doyle",
        "Icon", "Hercules", "Bauer", "Central Machinery",
        "Chicago Electric", "Braun", "Thunderbolt", "Warrior",
    ]

    def _build_search_url(self, keyword: str, in_store_only: bool, page: int = 1) -> str:
        """构建搜索URL"""
        encoded = quote_plus(keyword)
        url = f"{self.BASE_URL}/catalogsearch/result"
        params = {"q": encoded}
        if page > 1:
            params["p"] = str(page)
        return url + "?" + urlencode(params)

    async def _parse_search_results(self, page: Page) -> list[dict]:
        """解析搜索结果"""
        items = []
        try:
            await page.wait_for_selector(
                '.product-item, [data-testid="product-card"]',
                timeout=15000,
            )
            await self._scroll_to_bottom(page, max_scrolls=5)

            cards = await page.query_selector_all(
                '.product-item, [data-testid="product-card"]'
            )

            for card in cards:
                try:
                    item = {}

                    # 产品链接和名称
                    link_el = await card.query_selector(
                        "a.product-item-link, a.product-name"
                    )
                    if link_el:
                        href = await link_el.get_attribute("href")
                        item["product_url"] = href or ""
                        item["name"] = (await link_el.inner_text()).strip()

                    # 价格
                    price_el = await card.query_selector(
                        ".price-box .price, .product-price .price"
                    )
                    if price_el:
                        price_text = await price_el.inner_text()
                        price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                        if price_match:
                            item["price"] = float(price_match.group())

                    # 评分
                    rating_el = await card.query_selector(
                        '.rating-result, [data-testid="rating"]'
                    )
                    if rating_el:
                        # Harbor Freight uses percentage-based ratings
                        title = await rating_el.get_attribute("title") or ""
                        if not title:
                            inner_el = await rating_el.query_selector("span")
                            if inner_el:
                                title = await inner_el.get_attribute("style") or ""
                        pct_match = re.search(r"(\d+)%", title)
                        if pct_match:
                            item["rating"] = round(float(pct_match.group(1)) / 20, 1)

                    # 评论数
                    review_el = await card.query_selector(
                        '.reviews-actions .action, .review-count'
                    )
                    if review_el:
                        text = await review_el.inner_text()
                        match = re.search(r"(\d+)", text)
                        if match:
                            item["review_count"] = int(match.group(1))

                    # 品牌 (从名称中提取Harbor Freight自有品牌)
                    item["brand"] = self._extract_hf_brand(item.get("name", ""))

                    # 图片
                    img_el = await card.query_selector(
                        ".product-image-photo, img.product-image"
                    )
                    if img_el:
                        src = await img_el.get_attribute("src")
                        if not src:
                            src = await img_el.get_attribute("data-src")
                        if src:
                            item["image_url"] = src

                    # SKU (从URL或页面数据提取)
                    if item.get("product_url"):
                        # HF URLs typically end with SKU number
                        sku_match = re.search(r"-(\d{5,})\.html", item["product_url"])
                        if sku_match:
                            item["sku"] = sku_match.group(1)

                    # Harbor Freight products are generally in-store
                    item["in_store_only"] = True

                    if item.get("sku") and item.get("name"):
                        items.append(item)

                except Exception as e:
                    logger.debug(f"解析Harbor Freight产品卡片失败: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Harbor Freight搜索结果解析失败: {e}")

        return items

    def _extract_hf_brand(self, name: str) -> str:
        """提取Harbor Freight品牌"""
        name_lower = name.lower()
        for brand in self.HF_BRANDS:
            if name_lower.startswith(brand.lower()):
                return brand
        return "Harbor Freight"

    async def _has_next_page(self, page: Page) -> bool:
        """检查是否有下一页"""
        next_btn = await page.query_selector(
            'a.action.next, li.pages-item-next a'
        )
        return next_btn is not None

    async def search(
        self,
        keyword: str,
        in_store_only: bool = True,
        max_pages: int = 10,
    ) -> list[Product]:
        """搜索Harbor Freight产品"""
        products: list[Product] = []
        context = await self._new_context()

        try:
            page = await context.new_page()
            current_page = 1

            while current_page <= max_pages:
                url = self._build_search_url(keyword, in_store_only, current_page)
                logger.info(f"[Harbor Freight] 抓取第 {current_page} 页: {url}")

                await self._safe_goto(page, url)
                await self._random_delay()

                items = await self._parse_search_results(page)
                if not items:
                    logger.info(
                        f"[Harbor Freight] 第 {current_page} 页无结果，停止翻页"
                    )
                    break

                for item in items:
                    products.append(
                        Product(
                            sku=item.get("sku", ""),
                            name=item.get("name", ""),
                            brand=item.get("brand", "Harbor Freight"),
                            price=item.get("price", 0.0),
                            rating=item.get("rating"),
                            review_count=item.get("review_count", 0),
                            description="",
                            image_urls=[item["image_url"]] if item.get("image_url") else [],
                            product_url=item.get("product_url", ""),
                            retailer=self.RETAILER_NAME,
                            in_store_only=item.get("in_store_only", True),
                        )
                    )

                has_next = await self._has_next_page(page)
                if not has_next:
                    break

                current_page += 1
                await self._random_delay()

        except Exception as e:
            logger.error(f"[Harbor Freight] 搜索失败: {e}")
        finally:
            await context.close()

        logger.info(f"[Harbor Freight] 搜索 '{keyword}' 完成，共 {len(products)} 个产品")
        return products

    async def get_product_detail(self, url: str) -> Optional[Product]:
        """获取Harbor Freight产品详情"""
        context = await self._new_context()

        try:
            page = await context.new_page()
            await self._safe_goto(page, url, wait_until="networkidle")
            await self._random_delay()

            product_data: dict = {"product_url": url, "retailer": self.RETAILER_NAME}

            # 产品名称
            title_el = await page.query_selector(
                "h1.page-title span, h1[data-testid='product-title']"
            )
            if title_el:
                product_data["name"] = (await title_el.inner_text()).strip()

            # 价格
            price_el = await page.query_selector(
                '.price-box .price, [data-testid="product-price"]'
            )
            if price_el:
                price_text = await price_el.inner_text()
                price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                if price_match:
                    product_data["price"] = float(price_match.group())

            # 品牌
            product_data["brand"] = self._extract_hf_brand(
                product_data.get("name", "")
            )

            # 评分
            rating_el = await page.query_selector('.rating-result span[style]')
            if rating_el:
                style = await rating_el.get_attribute("style") or ""
                pct_match = re.search(r"(\d+)%", style)
                if pct_match:
                    product_data["rating"] = round(float(pct_match.group(1)) / 20, 1)

            # 评论数
            review_el = await page.query_selector('.reviews-actions a, .review-count')
            if review_el:
                text = await review_el.inner_text()
                match = re.search(r"(\d+)", text)
                if match:
                    product_data["review_count"] = int(match.group(1))

            # 描述
            desc_el = await page.query_selector(
                '.product-info-description .value, '
                '[data-testid="product-description"]'
            )
            if desc_el:
                product_data["description"] = (await desc_el.inner_text()).strip()

            # 规格
            specs = {}
            spec_rows = await page.query_selector_all(
                '.additional-attributes-wrapper tr, '
                '.product-specs-table tr'
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
                '.fotorama__stage img, .gallery-image img'
            )
            for img in img_els:
                src = await img.get_attribute("src")
                if src and "placeholder" not in src:
                    image_urls.append(src)
            product_data["image_urls"] = image_urls

            # SKU
            sku_el = await page.query_selector('.product-info-stock-sku .value, .sku .value')
            if sku_el:
                product_data["sku"] = (await sku_el.inner_text()).strip()
            else:
                sku_match = re.search(r"-(\d{5,})\.html", url)
                if sku_match:
                    product_data["sku"] = sku_match.group(1)

            return Product(
                sku=product_data.get("sku", ""),
                name=product_data.get("name", ""),
                brand=product_data.get("brand", "Harbor Freight"),
                price=product_data.get("price", 0.0),
                rating=product_data.get("rating"),
                review_count=product_data.get("review_count", 0),
                description=product_data.get("description", ""),
                specs=product_data.get("specs", {}),
                image_urls=product_data.get("image_urls", []),
                product_url=url,
                retailer=self.RETAILER_NAME,
                in_store_only=True,
            )

        except Exception as e:
            logger.error(f"[Harbor Freight] 产品详情获取失败 {url}: {e}")
            return None
        finally:
            await context.close()

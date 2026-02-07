"""Lowe's 适配器"""

import logging
import re
from typing import Optional
from urllib.parse import quote_plus, urlencode

from playwright.async_api import Page

from .base import Product, RetailerScraper

logger = logging.getLogger(__name__)


class LowesScraper(RetailerScraper):
    """Lowe's 产品数据爬虫

    支持功能：
    - 关键词搜索，可筛选 In-Store Only
    - 自动翻页采集
    - 产品详情页规格提取
    """

    RETAILER_NAME = "lowes"
    BASE_URL = "https://www.lowes.com"

    def _build_search_url(self, keyword: str, in_store_only: bool, page: int = 1) -> str:
        """构建搜索URL"""
        encoded = quote_plus(keyword)
        url = f"{self.BASE_URL}/search"
        params = {"searchTerm": encoded}
        if in_store_only:
            params["refinement"] = "4294967177"  # Lowe's in-store availability filter
        if page > 1:
            params["offset"] = str((page - 1) * 24)
        return url + "?" + urlencode(params)

    async def _parse_search_results(self, page: Page) -> list[dict]:
        """解析搜索结果"""
        items = []
        try:
            await page.wait_for_selector(
                '[data-selector="prd-card"], .plp-card',
                timeout=15000,
            )
            await self._scroll_to_bottom(page, max_scrolls=5)

            cards = await page.query_selector_all(
                '[data-selector="prd-card"], .plp-card'
            )

            for card in cards:
                try:
                    item = {}

                    # 产品链接和名称
                    link_el = await card.query_selector(
                        'a[data-selector="prd-ttl"], a.product-title'
                    )
                    if link_el:
                        href = await link_el.get_attribute("href")
                        item["product_url"] = (
                            f"{self.BASE_URL}{href}" if href and not href.startswith("http")
                            else href or ""
                        )
                        item["name"] = (await link_el.inner_text()).strip()

                    # 品牌
                    brand_el = await card.query_selector(
                        '[data-selector="prd-brand"], .product-brand'
                    )
                    if brand_el:
                        item["brand"] = (await brand_el.inner_text()).strip()

                    # 价格
                    price_el = await card.query_selector(
                        '[data-selector="prd-price"], .product-price'
                    )
                    if price_el:
                        price_text = await price_el.inner_text()
                        price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                        if price_match:
                            item["price"] = float(price_match.group())

                    # 评分
                    rating_el = await card.query_selector(
                        '[data-selector="prd-ratings"], .product-rating'
                    )
                    if rating_el:
                        aria_label = await rating_el.get_attribute("aria-label") or ""
                        rating_match = re.search(r"([\d.]+)\s*out", aria_label)
                        if rating_match:
                            item["rating"] = float(rating_match.group(1))
                        review_match = re.search(r"([\d,]+)\s*(?:review|rating)", aria_label)
                        if review_match:
                            item["review_count"] = int(
                                review_match.group(1).replace(",", "")
                            )

                    # 图片
                    img_el = await card.query_selector("img.product-image, img")
                    if img_el:
                        src = await img_el.get_attribute("src")
                        if src:
                            item["image_url"] = src

                    # SKU / 型号 (从URL提取)
                    if item.get("product_url"):
                        sku_match = re.search(r"/(\d{7,})", item["product_url"])
                        if sku_match:
                            item["sku"] = sku_match.group(1)

                    # 配送/库存标记
                    avail_el = await card.query_selector(
                        '[data-selector="prd-availability"], .fulfillment-option'
                    )
                    if avail_el:
                        text = await avail_el.inner_text()
                        item["in_store_only"] = (
                            "in store" in text.lower()
                            and "delivery" not in text.lower()
                            and "shipping" not in text.lower()
                        )

                    if item.get("sku") and item.get("name"):
                        items.append(item)

                except Exception as e:
                    logger.debug(f"解析Lowe's产品卡片失败: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Lowe's搜索结果解析失败: {e}")

        return items

    async def _has_next_page(self, page: Page) -> bool:
        """检查是否有下一页"""
        next_btn = await page.query_selector(
            'a[aria-label="Next Page"], '
            '.pagination a.next:not(.disabled)'
        )
        return next_btn is not None

    async def search(
        self,
        keyword: str,
        in_store_only: bool = True,
        max_pages: int = 10,
    ) -> list[Product]:
        """搜索Lowe's产品"""
        products: list[Product] = []
        context = await self._new_context()

        try:
            page = await context.new_page()
            current_page = 1

            while current_page <= max_pages:
                url = self._build_search_url(keyword, in_store_only, current_page)
                logger.info(f"[Lowe's] 抓取第 {current_page} 页: {url}")

                await self._safe_goto(page, url)
                await self._random_delay()

                items = await self._parse_search_results(page)
                if not items:
                    logger.info(f"[Lowe's] 第 {current_page} 页无结果，停止翻页")
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
            logger.error(f"[Lowe's] 搜索失败: {e}")
        finally:
            await context.close()

        logger.info(f"[Lowe's] 搜索 '{keyword}' 完成，共 {len(products)} 个产品")
        return products

    async def get_product_detail(self, url: str) -> Optional[Product]:
        """获取Lowe's产品详情"""
        context = await self._new_context()

        try:
            page = await context.new_page()
            await self._safe_goto(page, url, wait_until="networkidle")
            await self._random_delay()

            product_data: dict = {"product_url": url, "retailer": self.RETAILER_NAME}

            # 产品名称
            title_el = await page.query_selector("h1.product-title, h1[data-selector]")
            if title_el:
                product_data["name"] = (await title_el.inner_text()).strip()

            # 品牌
            brand_el = await page.query_selector(
                'a[data-selector="brand-name"], .product-brand-link'
            )
            if brand_el:
                product_data["brand"] = (await brand_el.inner_text()).strip()

            # 价格
            price_el = await page.query_selector(
                '[data-selector="price"], .main-price .price'
            )
            if price_el:
                price_text = await price_el.inner_text()
                price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                if price_match:
                    product_data["price"] = float(price_match.group())

            # 评分和评论
            rating_section = await page.query_selector('.ratings-reviews, [data-selector="ratings"]')
            if rating_section:
                text = await rating_section.inner_text()
                rating_match = re.search(r"([\d.]+)\s*out", text)
                if rating_match:
                    product_data["rating"] = float(rating_match.group(1))
                review_match = re.search(r"([\d,]+)\s*(?:review|rating)", text, re.IGNORECASE)
                if review_match:
                    product_data["review_count"] = int(
                        review_match.group(1).replace(",", "")
                    )

            # 描述
            desc_el = await page.query_selector(
                '[data-selector="product-description"], .product-description'
            )
            if desc_el:
                product_data["description"] = (await desc_el.inner_text()).strip()

            # 规格
            specs = {}
            spec_rows = await page.query_selector_all(
                '.specifications-table tr, '
                '[data-selector="specifications"] tr'
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
                '.hero-image img, [data-selector="gallery"] img'
            )
            for img in img_els:
                src = await img.get_attribute("src")
                if src and "placeholder" not in src:
                    image_urls.append(src)
            product_data["image_urls"] = image_urls

            # SKU
            sku_match = re.search(r"/(\d{7,})", url)
            product_data["sku"] = sku_match.group(1) if sku_match else ""

            # 型号
            model_el = await page.query_selector(
                '[data-selector="model-number"], .product-model-number'
            )
            if model_el:
                model_text = await model_el.inner_text()
                model_match = re.search(r"#?\s*(\S+)", model_text)
                if model_match:
                    product_data["model_number"] = model_match.group(1)

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
                model_number=product_data.get("model_number", ""),
            )

        except Exception as e:
            logger.error(f"[Lowe's] 产品详情获取失败 {url}: {e}")
            return None
        finally:
            await context.close()

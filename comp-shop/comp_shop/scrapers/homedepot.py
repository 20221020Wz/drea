"""Home Depot 适配器"""

import logging
import re
from typing import Optional
from urllib.parse import quote_plus, urlencode

from playwright.async_api import Page

from .base import Product, RetailerScraper

logger = logging.getLogger(__name__)


class HomeDepotScraper(RetailerScraper):
    """Home Depot 产品数据爬虫

    支持功能：
    - 关键词搜索，可筛选 In-Store Only
    - 自动翻页采集
    - 产品详情页规格提取
    """

    RETAILER_NAME = "homedepot"
    BASE_URL = "https://www.homedepot.com"

    def _build_search_url(self, keyword: str, in_store_only: bool, page: int = 1) -> str:
        """构建搜索URL"""
        encoded = quote_plus(keyword)
        url = f"{self.BASE_URL}/s/{encoded}"
        params = {}
        if in_store_only:
            params["NCNI-5"] = ""
            params["storeSelection"] = "true"
        if page > 1:
            params["Nao"] = str((page - 1) * 24)  # HD uses offset-based pagination
        if params:
            url += "?" + urlencode(params, doseq=True)
        return url

    async def _parse_search_results(self, page: Page) -> list[dict]:
        """从搜索结果页面解析产品卡片"""
        items = []
        try:
            # 等待产品网格加载
            await page.wait_for_selector(
                '[data-testid="product-pod"], .browse-search__pod',
                timeout=15000,
            )

            # 滚动加载所有产品
            await self._scroll_to_bottom(page, max_scrolls=5)

            # 提取产品信息
            cards = await page.query_selector_all(
                '[data-testid="product-pod"], .browse-search__pod'
            )

            for card in cards:
                try:
                    item = {}

                    # 产品链接和名称
                    link_el = await card.query_selector(
                        'a[data-testid="product-header"], a.product-pod--ie-background'
                    )
                    if link_el:
                        href = await link_el.get_attribute("href")
                        item["product_url"] = f"{self.BASE_URL}{href}" if href else ""
                        item["name"] = (await link_el.inner_text()).strip()

                    # 价格
                    price_el = await card.query_selector(
                        '[data-testid="price-format"] span, .price-format__main-price'
                    )
                    if price_el:
                        price_text = await price_el.inner_text()
                        price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                        item["price"] = float(price_match.group()) if price_match else 0.0

                    # 评分
                    rating_el = await card.query_selector(
                        '[data-testid="ratings"], .stars-reviews-count'
                    )
                    if rating_el:
                        rating_text = await rating_el.inner_text()
                        rating_match = re.search(r"([\d.]+)\s*out of", rating_text)
                        if rating_match:
                            item["rating"] = float(rating_match.group(1))
                        review_match = re.search(r"\(([\d,]+)\)", rating_text)
                        if review_match:
                            item["review_count"] = int(
                                review_match.group(1).replace(",", "")
                            )

                    # 品牌
                    brand_el = await card.query_selector(
                        '[data-testid="product-brand"], .product-pod__brand'
                    )
                    if brand_el:
                        item["brand"] = (await brand_el.inner_text()).strip()

                    # 图片
                    img_el = await card.query_selector("img")
                    if img_el:
                        src = await img_el.get_attribute("src")
                        if src:
                            item["image_url"] = src

                    # SKU (从URL中提取)
                    if item.get("product_url"):
                        sku_match = re.search(r"/(\d{9})", item["product_url"])
                        if sku_match:
                            item["sku"] = sku_match.group(1)

                    # In-Store Only标记
                    store_badge = await card.query_selector(
                        '[data-testid="store-only-badge"], .product-pod__fulfillment'
                    )
                    if store_badge:
                        badge_text = await store_badge.inner_text()
                        item["in_store_only"] = "in-store" in badge_text.lower()

                    if item.get("sku") and item.get("name"):
                        items.append(item)

                except Exception as e:
                    logger.debug(f"解析产品卡片失败: {e}")
                    continue

        except Exception as e:
            logger.warning(f"搜索结果页面解析失败: {e}")

        return items

    async def _has_next_page(self, page: Page) -> bool:
        """检查是否有下一页"""
        next_btn = await page.query_selector(
            'nav[aria-label="Pagination"] a[aria-label="Next"], '
            '.hd-pagination__next:not(.hd-pagination__link--disabled)'
        )
        return next_btn is not None

    async def search(
        self,
        keyword: str,
        in_store_only: bool = True,
        max_pages: int = 10,
    ) -> list[Product]:
        """搜索Home Depot产品"""
        products: list[Product] = []
        context = await self._new_context()

        try:
            page = await context.new_page()
            current_page = 1

            while current_page <= max_pages:
                url = self._build_search_url(keyword, in_store_only, current_page)
                logger.info(f"[Home Depot] 抓取第 {current_page} 页: {url}")

                await self._safe_goto(page, url)
                await self._random_delay()

                items = await self._parse_search_results(page)
                if not items:
                    logger.info(f"[Home Depot] 第 {current_page} 页无结果，停止翻页")
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
            logger.error(f"[Home Depot] 搜索失败: {e}")
        finally:
            await context.close()

        logger.info(f"[Home Depot] 搜索 '{keyword}' 完成，共 {len(products)} 个产品")
        return products

    async def get_product_detail(self, url: str) -> Optional[Product]:
        """获取Home Depot产品详情"""
        context = await self._new_context()

        try:
            page = await context.new_page()
            await self._safe_goto(page, url, wait_until="networkidle")
            await self._random_delay()

            product_data: dict = {"product_url": url, "retailer": self.RETAILER_NAME}

            # 产品名称
            title_el = await page.query_selector(
                'h1.product-details__title, [data-testid="product-title"]'
            )
            if title_el:
                product_data["name"] = (await title_el.inner_text()).strip()

            # 品牌
            brand_el = await page.query_selector(
                '.product-details__brand a, [data-testid="product-brand"]'
            )
            if brand_el:
                product_data["brand"] = (await brand_el.inner_text()).strip()

            # 价格
            price_el = await page.query_selector(
                '#standard-price span, [data-testid="price-format"]'
            )
            if price_el:
                price_text = await price_el.inner_text()
                price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                if price_match:
                    product_data["price"] = float(price_match.group())

            # 评分和评论数
            rating_el = await page.query_selector('[data-testid="ratings-section"]')
            if rating_el:
                rating_text = await rating_el.inner_text()
                rating_match = re.search(r"([\d.]+)\s*out", rating_text)
                if rating_match:
                    product_data["rating"] = float(rating_match.group(1))
                review_match = re.search(r"([\d,]+)\s*(?:Reviews|ratings)", rating_text)
                if review_match:
                    product_data["review_count"] = int(
                        review_match.group(1).replace(",", "")
                    )

            # SKU / 型号
            sku_el = await page.query_selector(
                '.product-info-bar__detail:has-text("Store SKU"), '
                '[data-testid="product-info-bar"]'
            )
            if sku_el:
                sku_text = await sku_el.inner_text()
                sku_match = re.search(r"(?:Store SKU|Internet)\s*#?\s*(\d+)", sku_text)
                if sku_match:
                    product_data["sku"] = sku_match.group(1)

            model_el = await page.query_selector('.product-info-bar__detail:has-text("Model")')
            if model_el:
                model_text = await model_el.inner_text()
                model_match = re.search(r"Model\s*#?\s*(\S+)", model_text)
                if model_match:
                    product_data["model_number"] = model_match.group(1)

            # 产品描述
            desc_el = await page.query_selector(
                '.desktop-content-wrapper__main-description, '
                '[data-testid="product-description"]'
            )
            if desc_el:
                product_data["description"] = (await desc_el.inner_text()).strip()

            # 规格参数
            specs = {}
            spec_rows = await page.query_selector_all(
                '.specifications__group .specifications__row, '
                '[data-testid="specs-table"] tr'
            )
            for row in spec_rows:
                cells = await row.query_selector_all("td, th, .specifications__cell")
                if len(cells) >= 2:
                    key = (await cells[0].inner_text()).strip()
                    value = (await cells[1].inner_text()).strip()
                    if key and value:
                        specs[key] = value
            product_data["specs"] = specs

            # 产品图片
            image_urls = []
            img_els = await page.query_selector_all(
                '.mediagallery__mainimage img, [data-testid="media-gallery"] img'
            )
            for img in img_els:
                src = await img.get_attribute("src")
                if src and "placeholder" not in src:
                    image_urls.append(src)
            product_data["image_urls"] = image_urls

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
            logger.error(f"[Home Depot] 产品详情获取失败 {url}: {e}")
            return None
        finally:
            await context.close()

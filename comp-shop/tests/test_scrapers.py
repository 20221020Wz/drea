"""爬虫模块测试 - 单元测试（不需要网络）"""

import pytest

from comp_shop.scrapers import SCRAPER_REGISTRY, get_scraper
from comp_shop.scrapers.base import Product, RetailerScraper
from comp_shop.scrapers.homedepot import HomeDepotScraper
from comp_shop.scrapers.walmart import WalmartScraper
from comp_shop.scrapers.lowes import LowesScraper
from comp_shop.scrapers.harborfreight import HarborFreightScraper


class TestScraperRegistry:
    def test_all_scrapers_registered(self):
        assert "homedepot" in SCRAPER_REGISTRY
        assert "walmart" in SCRAPER_REGISTRY
        assert "lowes" in SCRAPER_REGISTRY
        assert "harborfreight" in SCRAPER_REGISTRY

    def test_get_scraper(self):
        scraper = get_scraper("homedepot")
        assert isinstance(scraper, HomeDepotScraper)

        scraper = get_scraper("walmart")
        assert isinstance(scraper, WalmartScraper)

        scraper = get_scraper("lowes")
        assert isinstance(scraper, LowesScraper)

        scraper = get_scraper("harborfreight")
        assert isinstance(scraper, HarborFreightScraper)

    def test_get_scraper_invalid(self):
        with pytest.raises(ValueError, match="未知的零售商"):
            get_scraper("amazon")


class TestProduct:
    def test_product_creation(self):
        product = Product(
            sku="123456",
            name="Test Pliers",
            brand="TestBrand",
            price=19.99,
            rating=4.5,
            review_count=100,
            description="Test description",
            specs={"size": "8 in."},
            image_urls=["https://example.com/img.jpg"],
            product_url="https://example.com/product/123456",
            retailer="homedepot",
            in_store_only=True,
        )
        assert product.sku == "123456"
        assert product.price == 19.99
        assert product.in_store_only is True

    def test_product_to_dict(self):
        product = Product(
            sku="SKU001",
            name="Test",
            brand="Brand",
            price=10.0,
            rating=None,
            review_count=0,
            description="",
            retailer="walmart",
        )
        d = product.to_dict()
        assert d["sku"] == "SKU001"
        assert d["retailer"] == "walmart"
        assert d["rating"] is None
        assert isinstance(d["specs"], dict)
        assert isinstance(d["image_urls"], list)

    def test_product_defaults(self):
        product = Product(
            sku="X",
            name="Y",
            brand="Z",
            price=0,
            rating=None,
            review_count=0,
            description="",
        )
        assert product.specs == {}
        assert product.image_urls == []
        assert product.product_url == ""
        assert product.retailer == ""
        assert product.in_store_only is False


class TestHomeDepotScraper:
    def test_init(self):
        scraper = HomeDepotScraper()
        assert scraper.RETAILER_NAME == "homedepot"
        assert "homedepot.com" in scraper.BASE_URL

    def test_build_search_url(self):
        scraper = HomeDepotScraper()
        url = scraper._build_search_url("pliers", in_store_only=True, page=1)
        assert "homedepot.com/s/pliers" in url
        assert "storeSelection" in url

    def test_build_search_url_no_filter(self):
        scraper = HomeDepotScraper()
        url = scraper._build_search_url("pliers", in_store_only=False, page=1)
        assert "storeSelection" not in url

    def test_build_search_url_pagination(self):
        scraper = HomeDepotScraper()
        url = scraper._build_search_url("pliers", in_store_only=False, page=3)
        assert "Nao=" in url  # HD uses offset-based pagination


class TestWalmartScraper:
    def test_init(self):
        scraper = WalmartScraper()
        assert scraper.RETAILER_NAME == "walmart"
        assert "walmart.com" in scraper.BASE_URL

    def test_build_search_url(self):
        scraper = WalmartScraper()
        url = scraper._build_search_url("pliers", in_store_only=True, page=1)
        assert "walmart.com/search" in url
        assert "q=pliers" in url
        assert "fulfillment_method_in_store" in url

    def test_extract_brand_from_name(self):
        assert WalmartScraper._extract_brand_from_name("CRAFTSMAN 8in Pliers") == "CRAFTSMAN"
        assert WalmartScraper._extract_brand_from_name("Milwaukee Tool Set") == "Milwaukee"
        assert WalmartScraper._extract_brand_from_name("Klein Tools 8in") == "Klein Tools"
        assert WalmartScraper._extract_brand_from_name("Unknown Brand Pliers") == "Unknown"


class TestLowesScraper:
    def test_init(self):
        scraper = LowesScraper()
        assert scraper.RETAILER_NAME == "lowes"
        assert "lowes.com" in scraper.BASE_URL

    def test_build_search_url(self):
        scraper = LowesScraper()
        url = scraper._build_search_url("pliers", in_store_only=True, page=1)
        assert "lowes.com/search" in url
        assert "searchTerm=pliers" in url


class TestHarborFreightScraper:
    def test_init(self):
        scraper = HarborFreightScraper()
        assert scraper.RETAILER_NAME == "harborfreight"
        assert "harborfreight.com" in scraper.BASE_URL

    def test_extract_hf_brand(self):
        scraper = HarborFreightScraper()
        assert scraper._extract_hf_brand("Pittsburgh Pro 8in Pliers") == "Pittsburgh Pro"
        assert scraper._extract_hf_brand("Quinn Diagonal Pliers") == "Quinn"
        assert scraper._extract_hf_brand("Doyle Linesman Pliers") == "Doyle"
        assert scraper._extract_hf_brand("Unknown Product") == "Harbor Freight"

    def test_build_search_url(self):
        scraper = HarborFreightScraper()
        url = scraper._build_search_url("pliers", in_store_only=True, page=2)
        assert "harborfreight.com/catalogsearch" in url
        assert "q=pliers" in url
        assert "p=2" in url

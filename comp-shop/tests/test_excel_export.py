"""Excel导出模块测试"""

import os
import tempfile

import pytest

from comp_shop.export.excel import ExcelExporter, export_full_report


@pytest.fixture
def sample_products():
    """测试用产品数据"""
    return [
        {
            "sku": "HD001",
            "name": "Milwaukee 8 in. Long Nose Pliers",
            "brand": "Milwaukee",
            "price": 19.97,
            "rating": 4.7,
            "review_count": 245,
            "retailer": "homedepot",
            "in_store_only": True,
            "product_url": "https://www.homedepot.com/p/123",
            "image_urls": ["https://img.example.com/1.jpg"],
            "specs": {"size": "8 in.", "type": "Long Nose Pliers"},
        },
        {
            "sku": "WM001",
            "name": "CRAFTSMAN 8 in. Long Nose Pliers",
            "brand": "Craftsman",
            "price": 12.98,
            "rating": 4.5,
            "review_count": 87,
            "retailer": "walmart",
            "in_store_only": False,
            "product_url": "https://www.walmart.com/ip/123",
            "image_urls": [],
            "specs": {"size": "8 in.", "type": "Long Nose Pliers"},
        },
        {
            "sku": "WM002",
            "name": "IRWIN 10 in. Locking Pliers",
            "brand": "Irwin",
            "price": 15.98,
            "rating": 4.6,
            "review_count": 456,
            "retailer": "walmart",
            "in_store_only": False,
            "product_url": "https://www.walmart.com/ip/456",
            "image_urls": [],
            "specs": {"size": "10 in.", "type": "Locking Pliers"},
        },
    ]


@pytest.fixture
def sample_gaps():
    return [
        {
            "gap_type": "complete_gap",
            "target_retailer": "homedepot",
            "dimension": "size",
            "dimension_value": "10 in.",
            "competitors_count": 2,
            "competitor_examples": [
                "[walmart] IRWIN 10in Locking Pliers ($15.98)",
            ],
            "priority_score": 8.5,
            "recommendation": "建议开发10寸规格产品",
        },
    ]


@pytest.fixture
def sample_summary():
    return {
        "homedepot": {
            "product_count": 1,
            "brand_count": 1,
            "brands": ["Milwaukee"],
            "price_range": {"min": 19.97, "max": 19.97, "avg": 19.97},
            "avg_rating": 4.7,
            "total_reviews": 245,
        },
        "walmart": {
            "product_count": 2,
            "brand_count": 2,
            "brands": ["Craftsman", "Irwin"],
            "price_range": {"min": 12.98, "max": 15.98, "avg": 14.48},
            "avg_rating": 4.55,
            "total_reviews": 543,
        },
    }


class TestExcelExporter:
    def test_create_exporter(self, tmp_path):
        output_path = tmp_path / "test.xlsx"
        exporter = ExcelExporter(output_path)
        assert exporter.output_path == output_path

    def test_add_raw_data_sheets(self, sample_products, tmp_path):
        output_path = tmp_path / "test_raw.xlsx"
        exporter = ExcelExporter(output_path)

        products_by_retailer = {}
        for p in sample_products:
            retailer = p["retailer"]
            if retailer not in products_by_retailer:
                products_by_retailer[retailer] = []
            products_by_retailer[retailer].append(p)

        exporter.add_raw_data_sheets(products_by_retailer)
        filepath = exporter.save()

        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 0

    def test_add_comparison_matrix(self, sample_products, tmp_path):
        output_path = tmp_path / "test_matrix.xlsx"
        exporter = ExcelExporter(output_path)

        exporter.add_comparison_matrix(
            sample_products, primary_dimension="size", primary_label="Size"
        )
        filepath = exporter.save()
        assert os.path.exists(filepath)

    def test_add_gap_analysis_sheet(self, sample_gaps, tmp_path):
        output_path = tmp_path / "test_gaps.xlsx"
        exporter = ExcelExporter(output_path)

        exporter.add_gap_analysis_sheet(sample_gaps)
        filepath = exporter.save()
        assert os.path.exists(filepath)

    def test_add_summary_sheet(self, sample_summary, tmp_path):
        output_path = tmp_path / "test_summary.xlsx"
        exporter = ExcelExporter(output_path)

        exporter.add_summary_sheet(sample_summary)
        filepath = exporter.save()
        assert os.path.exists(filepath)

    def test_full_report(self, sample_products, sample_gaps, sample_summary, tmp_path):
        output_path = tmp_path / "full_report.xlsx"
        filepath = export_full_report(
            products=sample_products,
            gaps=sample_gaps,
            summary=sample_summary,
            primary_dimension="size",
            output_path=output_path,
            primary_label="Size",
        )
        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 5000  # Should be a reasonable size

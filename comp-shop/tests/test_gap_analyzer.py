"""Gap分析引擎测试"""

import pytest

from comp_shop.analysis.gap_analyzer import GapAnalyzer, GapOpportunity, GapType


@pytest.fixture
def sample_products():
    """测试用产品数据 - 模拟Plier品类"""
    return [
        # Home Depot products
        {
            "sku": "HD001",
            "name": "Milwaukee 8 in. Long Nose Pliers",
            "brand": "Milwaukee",
            "price": 19.97,
            "rating": 4.7,
            "review_count": 245,
            "retailer": "homedepot",
            "specs": {"size": "8 in.", "type": "Long Nose Pliers"},
        },
        {
            "sku": "HD002",
            "name": "Milwaukee 6 in. Diagonal Cutting Pliers",
            "brand": "Milwaukee",
            "price": 14.97,
            "rating": 4.8,
            "review_count": 189,
            "retailer": "homedepot",
            "specs": {"size": "6 in.", "type": "Diagonal Cutting Pliers"},
        },
        {
            "sku": "HD003",
            "name": "Klein Tools 8 in. Tongue and Groove Pliers",
            "brand": "Klein Tools",
            "price": 24.97,
            "rating": 4.6,
            "review_count": 312,
            "retailer": "homedepot",
            "specs": {"size": "8 in.", "type": "Tongue and Groove Pliers"},
        },
        # Walmart products
        {
            "sku": "WM001",
            "name": "CRAFTSMAN 8 in. Long Nose Pliers",
            "brand": "Craftsman",
            "price": 12.98,
            "rating": 4.5,
            "review_count": 87,
            "retailer": "walmart",
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
            "specs": {"size": "10 in.", "type": "Locking Pliers"},
        },
        {
            "sku": "WM003",
            "name": "CRAFTSMAN 6 in. Slip Joint Pliers",
            "brand": "Craftsman",
            "price": 9.98,
            "rating": 4.3,
            "review_count": 65,
            "retailer": "walmart",
            "specs": {"size": "6 in.", "type": "Slip Joint Pliers"},
        },
        # Lowe's products
        {
            "sku": "LW001",
            "name": "Kobalt 8 in. Long Nose Pliers",
            "brand": "Kobalt",
            "price": 11.98,
            "rating": 4.2,
            "review_count": 45,
            "retailer": "lowes",
            "specs": {"size": "8 in.", "type": "Long Nose Pliers"},
        },
        {
            "sku": "LW002",
            "name": "Knipex 10 in. Cobra Pliers",
            "brand": "Knipex",
            "price": 42.98,
            "rating": 4.9,
            "review_count": 890,
            "retailer": "lowes",
            "specs": {"size": "10 in.", "type": "Tongue and Groove Pliers"},
        },
        {
            "sku": "LW003",
            "name": "Channellock 10 in. Locking Pliers",
            "brand": "Channellock",
            "price": 18.98,
            "rating": 4.5,
            "review_count": 234,
            "retailer": "lowes",
            "specs": {"size": "10 in.", "type": "Locking Pliers"},
        },
        # Harbor Freight products
        {
            "sku": "HF001",
            "name": "Pittsburgh 8 in. Long Nose Pliers",
            "brand": "Pittsburgh",
            "price": 5.99,
            "rating": 4.0,
            "review_count": 120,
            "retailer": "harborfreight",
            "specs": {"size": "8 in.", "type": "Long Nose Pliers"},
        },
        {
            "sku": "HF002",
            "name": "Pittsburgh 10 in. Locking Pliers",
            "brand": "Pittsburgh",
            "price": 7.99,
            "rating": 3.8,
            "review_count": 95,
            "retailer": "harborfreight",
            "specs": {"size": "10 in.", "type": "Locking Pliers"},
        },
        {
            "sku": "HF003",
            "name": "Quinn 12 in. Tongue and Groove Pliers",
            "brand": "Quinn",
            "price": 12.99,
            "rating": 4.3,
            "review_count": 67,
            "retailer": "harborfreight",
            "specs": {"size": "12 in.", "type": "Tongue and Groove Pliers"},
        },
    ]


class TestGapAnalyzer:
    def test_init(self, sample_products):
        analyzer = GapAnalyzer(sample_products)
        assert len(analyzer.products) == 12
        assert len(analyzer.retailer_groups) == 4
        assert "homedepot" in analyzer.retailer_groups
        assert "walmart" in analyzer.retailer_groups
        assert "lowes" in analyzer.retailer_groups
        assert "harborfreight" in analyzer.retailer_groups

    def test_get_coverage_summary(self, sample_products):
        analyzer = GapAnalyzer(sample_products)
        summary = analyzer.get_coverage_summary()

        assert "homedepot" in summary
        assert summary["homedepot"]["product_count"] == 3
        assert summary["homedepot"]["brand_count"] == 2  # Milwaukee, Klein Tools
        assert summary["homedepot"]["price_range"]["min"] == 14.97
        assert summary["homedepot"]["price_range"]["max"] == 24.97

        assert summary["harborfreight"]["product_count"] == 3

    def test_find_complete_gaps_size(self, sample_products):
        """HD缺少10寸和12寸产品"""
        analyzer = GapAnalyzer(sample_products)
        gaps = analyzer.find_complete_gaps("homedepot", "size")

        # Home Depot只有 6in 和 8in，缺少 10in 和 12in
        gap_values = {g.dimension_value for g in gaps}
        assert "10 in." in gap_values  # 3家竞品有10in (walmart, lowes, hf)
        # 12in 只有 harborfreight 有，min_competitors=2, 所以可能不在列表中

    def test_find_complete_gaps_type(self, sample_products):
        """HD缺少Locking Pliers和Slip Joint Pliers"""
        analyzer = GapAnalyzer(sample_products)
        gaps = analyzer.find_complete_gaps("homedepot", "type")

        gap_values = {g.dimension_value for g in gaps}
        assert "Locking Pliers" in gap_values  # walmart, lowes, hf都有

    def test_find_brand_gaps(self, sample_products):
        """分析品牌空缺"""
        analyzer = GapAnalyzer(sample_products)
        gaps = analyzer.find_brand_gaps("homedepot", min_competitors=2)

        gap_brands = {g.dimension_value for g in gaps}
        # Pittsburgh在walmart和harborfreight都没有 (只在hf)
        # Craftsman在walmart有 (只有1家)
        # 需要至少2家竞争对手才算gap

    def test_find_price_band_gaps(self, sample_products):
        """分析价格带空缺"""
        analyzer = GapAnalyzer(sample_products)
        gaps = analyzer.find_price_band_gaps("homedepot")

        # Home Depot价格在 $14.97-$24.97
        # 缺少 $0-10 区间（HF有大量低价产品）
        gap_bands = {g.dimension_value for g in gaps}
        assert "$0-10" in gap_bands

    def test_analyze_all(self, sample_products):
        """完整分析"""
        analyzer = GapAnalyzer(sample_products)
        results = analyzer.analyze_all("homedepot", dimensions=["size", "type"])

        assert len(results) > 0
        # 应该包含各种gap类型
        all_gaps = []
        for gaps in results.values():
            all_gaps.extend(gaps)
        assert len(all_gaps) > 0

    def test_gap_priority_scoring(self, sample_products):
        """验证优先级评分"""
        analyzer = GapAnalyzer(sample_products)
        gaps = analyzer.find_complete_gaps("homedepot", "type")

        for gap in gaps:
            assert 0 <= gap.priority_score <= 10
            assert gap.competitors_count >= 2

        # Locking Pliers应该是高优先级 (3家竞品都有)
        locking_gaps = [g for g in gaps if g.dimension_value == "Locking Pliers"]
        if locking_gaps:
            assert locking_gaps[0].competitors_count == 3

    def test_gap_to_dict(self, sample_products):
        """验证Gap序列化"""
        analyzer = GapAnalyzer(sample_products)
        gaps = analyzer.find_complete_gaps("homedepot", "size")

        for gap in gaps:
            d = gap.to_dict()
            assert "gap_type" in d
            assert "target_retailer" in d
            assert "dimension_value" in d
            assert "priority_score" in d
            assert isinstance(d["competitor_examples"], list)

    def test_empty_retailer(self, sample_products):
        """分析不存在的零售商"""
        analyzer = GapAnalyzer(sample_products)
        results = analyzer.analyze_all("nonexistent", dimensions=["size"])
        assert results == {}

    def test_competitor_examples(self, sample_products):
        """验证竞争对手示例"""
        analyzer = GapAnalyzer(sample_products)
        gaps = analyzer.find_complete_gaps("homedepot", "type")

        for gap in gaps:
            assert len(gap.competitor_examples) > 0
            for example in gap.competitor_examples:
                assert "[" in example  # 应包含零售商名
                assert "$" in example  # 应包含价格


class TestGapOpportunity:
    def test_creation(self):
        gap = GapOpportunity(
            gap_type=GapType.COMPLETE,
            target_retailer="homedepot",
            dimension="size",
            dimension_value="10 in.",
            competitors_count=3,
            competitor_examples=["[walmart] IRWIN 10in Pliers ($15.98)"],
            priority_score=8.5,
            recommendation="建议开发10寸规格产品",
        )
        assert gap.gap_type == GapType.COMPLETE
        assert gap.priority_score == 8.5

    def test_to_dict(self):
        gap = GapOpportunity(
            gap_type=GapType.BRAND,
            target_retailer="walmart",
            dimension="brand",
            dimension_value="Knipex",
            competitors_count=1,
        )
        d = gap.to_dict()
        assert d["gap_type"] == "brand_gap"
        assert d["target_retailer"] == "walmart"

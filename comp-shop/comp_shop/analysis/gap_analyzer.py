"""Gap分析引擎 - 识别市场空缺和竞争机会"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GapType(str, Enum):
    COMPLETE = "complete_gap"       # 完全空缺：目标零售商该规格产品数量为0
    BRAND = "brand_gap"             # 品牌空缺：缺少主流品牌
    PRICE_BAND = "price_band_gap"   # 价格带空缺：某价格区间产品密度低
    FEATURE = "feature_gap"         # 功能空缺：热门功能覆盖率低


@dataclass
class GapOpportunity:
    """市场空缺机会"""

    gap_type: GapType
    target_retailer: str
    dimension: str
    dimension_value: str
    competitors_count: int
    competitor_examples: list[str] = field(default_factory=list)
    priority_score: float = 0.0
    recommendation: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "gap_type": self.gap_type.value,
            "target_retailer": self.target_retailer,
            "dimension": self.dimension,
            "dimension_value": self.dimension_value,
            "competitors_count": self.competitors_count,
            "competitor_examples": self.competitor_examples,
            "priority_score": self.priority_score,
            "recommendation": self.recommendation,
            "details": self.details,
        }


class GapAnalyzer:
    """Gap分析引擎

    分析产品数据，识别目标零售商与竞争对手之间的产品覆盖差异，
    按规格、品牌、价格带、功能四个维度发现市场机会。
    """

    # 默认价格带划分 (美元)
    DEFAULT_PRICE_BANDS = [
        (0, 10, "$0-10"),
        (10, 20, "$10-20"),
        (20, 30, "$20-30"),
        (30, 50, "$30-50"),
        (50, 100, "$50-100"),
        (100, 200, "$100-200"),
        (200, float("inf"), "$200+"),
    ]

    def __init__(self, products: list[dict]):
        """
        Args:
            products: 产品数据列表，每个产品应包含 retailer, sku, name, brand,
                      price, specs 等字段
        """
        self.products = products
        self.retailer_groups = self._group_by_retailer()
        self._all_retailers = list(self.retailer_groups.keys())

    def _group_by_retailer(self) -> dict[str, list[dict]]:
        """按零售商分组"""
        groups: dict[str, list[dict]] = defaultdict(list)
        for product in self.products:
            retailer = product.get("retailer", "unknown")
            groups[retailer].append(product)
        return dict(groups)

    def _get_dimension_values(
        self, retailer: str, dimension: str
    ) -> list[str]:
        """获取某零售商在某维度下的所有值"""
        products = self.retailer_groups.get(retailer, [])
        values = []
        for p in products:
            specs = p.get("specs", {})
            value = specs.get(dimension) or p.get(dimension)
            if value and value != "null" and str(value).strip():
                values.append(str(value).strip())
        return values

    def _count_competitors_with_value(
        self,
        dimension: str,
        value: str,
        exclude_retailer: str = "",
    ) -> int:
        """统计有该维度值产品的竞争对手数量"""
        count = 0
        for retailer in self._all_retailers:
            if retailer == exclude_retailer:
                continue
            values = self._get_dimension_values(retailer, dimension)
            if value in values:
                count += 1
        return count

    def _get_competitor_examples(
        self,
        dimension: str,
        value: str,
        exclude_retailer: str = "",
        max_examples: int = 5,
    ) -> list[str]:
        """获取竞争对手拥有该维度值的产品示例"""
        examples = []
        for retailer, products in self.retailer_groups.items():
            if retailer == exclude_retailer:
                continue
            for p in products:
                specs = p.get("specs", {})
                p_value = specs.get(dimension) or p.get(dimension)
                if str(p_value).strip() == value:
                    price = p.get("price", 0)
                    name = p.get("name", "Unknown")
                    examples.append(
                        f"[{retailer}] {name} (${price:.2f})"
                    )
                    if len(examples) >= max_examples:
                        return examples
        return examples

    def _calculate_priority(
        self,
        dimension: str,
        value: str,
        competitors_count: int,
        target_retailer: str,
    ) -> float:
        """计算Gap机会的优先级分数 (0-10)

        评分因子：
        - 竞争对手覆盖数 (越多说明市场需求越确定)
        - 竞争对手产品的平均评分 (高评分说明市场接受度好)
        - 竞争对手产品的评论数量 (多评论说明销量高)
        - 价格区间可行性
        """
        score = 0.0

        # 因子1: 竞争对手覆盖数 (最高3分)
        competitor_score = min(competitors_count / len(self._all_retailers) * 4, 3.0)
        score += competitor_score

        # 因子2: 竞品平均评分 (最高2.5分)
        ratings = []
        review_counts = []
        for retailer, products in self.retailer_groups.items():
            if retailer == target_retailer:
                continue
            for p in products:
                specs = p.get("specs", {})
                p_value = specs.get(dimension) or p.get(dimension)
                if str(p_value).strip() == value:
                    if p.get("rating"):
                        ratings.append(p["rating"])
                    review_counts.append(p.get("review_count", 0))

        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            score += (avg_rating / 5) * 2.5

        # 因子3: 竞品评论量 (最高2.5分, 说明市场活跃度)
        if review_counts:
            avg_reviews = sum(review_counts) / len(review_counts)
            # 100条评论以上满分
            review_score = min(avg_reviews / 100, 1.0) * 2.5
            score += review_score

        # 因子4: 维度价值权重 (最高2分)
        high_value_dimensions = {"size", "type", "price_band"}
        if dimension in high_value_dimensions:
            score += 2.0
        else:
            score += 1.0

        return round(min(score, 10.0), 1)

    # ──────────────────── 完全空缺分析 ────────────────────

    def find_complete_gaps(
        self,
        target_retailer: str,
        dimension: str,
        min_competitors: int = 2,
    ) -> list[GapOpportunity]:
        """找出目标零售商完全缺失的规格/类型

        Args:
            target_retailer: 目标零售商
            dimension: 分析维度 (如 "size", "type")
            min_competitors: 最少有多少竞争对手有该值才算Gap

        Returns:
            Gap机会列表，按优先级排序
        """
        target_values = set(self._get_dimension_values(target_retailer, dimension))
        all_other_values: dict[str, int] = Counter()

        for retailer in self._all_retailers:
            if retailer == target_retailer:
                continue
            for value in set(self._get_dimension_values(retailer, dimension)):
                all_other_values[value] += 1

        gaps = []
        for value, count in all_other_values.items():
            if value not in target_values and count >= min_competitors:
                examples = self._get_competitor_examples(
                    dimension, value, exclude_retailer=target_retailer
                )
                priority = self._calculate_priority(
                    dimension, value, count, target_retailer
                )
                gaps.append(
                    GapOpportunity(
                        gap_type=GapType.COMPLETE,
                        target_retailer=target_retailer,
                        dimension=dimension,
                        dimension_value=value,
                        competitors_count=count,
                        competitor_examples=examples,
                        priority_score=priority,
                        recommendation=(
                            f"建议为{target_retailer}开发{dimension}={value}的产品，"
                            f"当前有{count}家竞争对手覆盖该规格"
                        ),
                    )
                )

        return sorted(gaps, key=lambda x: x.priority_score, reverse=True)

    # ──────────────────── 品牌空缺分析 ────────────────────

    def find_brand_gaps(
        self,
        target_retailer: str,
        min_competitors: int = 2,
    ) -> list[GapOpportunity]:
        """找出目标零售商缺少的主流品牌

        Args:
            target_retailer: 目标零售商
            min_competitors: 品牌在多少竞争对手出现才算主流

        Returns:
            品牌Gap列表
        """
        target_brands = set()
        for p in self.retailer_groups.get(target_retailer, []):
            brand = p.get("brand", "").strip()
            if brand:
                target_brands.add(brand)

        competitor_brands: dict[str, set[str]] = defaultdict(set)
        for retailer, products in self.retailer_groups.items():
            if retailer == target_retailer:
                continue
            for p in products:
                brand = p.get("brand", "").strip()
                if brand:
                    competitor_brands[brand].add(retailer)

        gaps = []
        for brand, retailers in competitor_brands.items():
            if brand not in target_brands and len(retailers) >= min_competitors:
                # 收集该品牌的产品示例
                examples = []
                brand_ratings = []
                brand_reviews = []
                for retailer in retailers:
                    for p in self.retailer_groups[retailer]:
                        if p.get("brand", "").strip() == brand:
                            price = p.get("price", 0)
                            examples.append(
                                f"[{retailer}] {p.get('name', '')} (${price:.2f})"
                            )
                            if p.get("rating"):
                                brand_ratings.append(p["rating"])
                            brand_reviews.append(p.get("review_count", 0))

                # 品牌优先级计算
                priority = min(len(retailers) / len(self._all_retailers) * 4, 3.0)
                if brand_ratings:
                    priority += (sum(brand_ratings) / len(brand_ratings) / 5) * 3.5
                if brand_reviews:
                    avg_reviews = sum(brand_reviews) / len(brand_reviews)
                    priority += min(avg_reviews / 100, 1.0) * 3.5

                gaps.append(
                    GapOpportunity(
                        gap_type=GapType.BRAND,
                        target_retailer=target_retailer,
                        dimension="brand",
                        dimension_value=brand,
                        competitors_count=len(retailers),
                        competitor_examples=examples[:5],
                        priority_score=round(min(priority, 10.0), 1),
                        recommendation=(
                            f"{target_retailer}缺少{brand}品牌产品，"
                            f"该品牌在{len(retailers)}家竞争对手有售"
                        ),
                        details={
                            "avg_rating": (
                                round(sum(brand_ratings) / len(brand_ratings), 1)
                                if brand_ratings
                                else None
                            ),
                            "total_products_at_competitors": len(examples),
                        },
                    )
                )

        return sorted(gaps, key=lambda x: x.priority_score, reverse=True)

    # ──────────────────── 价格带空缺分析 ────────────────────

    def find_price_band_gaps(
        self,
        target_retailer: str,
        price_bands: Optional[list[tuple]] = None,
        density_threshold: float = 0.3,
    ) -> list[GapOpportunity]:
        """找出目标零售商产品密度明显低于竞争对手的价格区间

        Args:
            target_retailer: 目标零售商
            price_bands: 自定义价格带 [(min, max, label), ...]
            density_threshold: 密度差异阈值（竞品平均密度的比例）

        Returns:
            价格带Gap列表
        """
        bands = price_bands or self.DEFAULT_PRICE_BANDS

        def get_band(price: float) -> Optional[str]:
            for low, high, label in bands:
                if low <= price < high:
                    return label
            return None

        # 统计各零售商各价格带的产品数
        band_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for retailer, products in self.retailer_groups.items():
            for p in products:
                price = p.get("price", 0)
                band = get_band(price)
                if band:
                    band_counts[retailer][band] += 1

        target_counts = band_counts.get(target_retailer, {})
        competitor_retailers = [r for r in self._all_retailers if r != target_retailer]

        gaps = []
        for _, _, label in bands:
            target_count = target_counts.get(label, 0)

            # 计算竞争对手在该价格带的平均产品数
            comp_counts = [
                band_counts.get(r, {}).get(label, 0) for r in competitor_retailers
            ]
            if not comp_counts:
                continue
            avg_comp_count = sum(comp_counts) / len(comp_counts)

            # 如果目标零售商的产品数显著低于竞品平均
            if avg_comp_count > 0 and (
                target_count == 0
                or target_count / avg_comp_count < density_threshold
            ):
                competitors_with_products = sum(1 for c in comp_counts if c > 0)

                # 收集该价格带的竞品示例
                examples = []
                for retailer in competitor_retailers:
                    for p in self.retailer_groups.get(retailer, []):
                        band = get_band(p.get("price", 0))
                        if band == label:
                            examples.append(
                                f"[{retailer}] {p.get('name', '')} "
                                f"(${p.get('price', 0):.2f})"
                            )
                            if len(examples) >= 5:
                                break
                    if len(examples) >= 5:
                        break

                priority = self._calculate_priority(
                    "price_band", label, competitors_with_products, target_retailer
                )

                gaps.append(
                    GapOpportunity(
                        gap_type=GapType.PRICE_BAND,
                        target_retailer=target_retailer,
                        dimension="price_band",
                        dimension_value=label,
                        competitors_count=competitors_with_products,
                        competitor_examples=examples,
                        priority_score=priority,
                        recommendation=(
                            f"{target_retailer}在{label}价格带仅有{target_count}个产品，"
                            f"竞争对手平均有{avg_comp_count:.0f}个"
                        ),
                        details={
                            "target_count": target_count,
                            "avg_competitor_count": round(avg_comp_count, 1),
                            "density_ratio": (
                                round(target_count / avg_comp_count, 2)
                                if avg_comp_count > 0
                                else 0
                            ),
                        },
                    )
                )

        return sorted(gaps, key=lambda x: x.priority_score, reverse=True)

    # ──────────────────── 功能空缺分析 ────────────────────

    def find_feature_gaps(
        self,
        target_retailer: str,
        feature_field: str = "features",
        min_competitors: int = 2,
    ) -> list[GapOpportunity]:
        """找出目标零售商覆盖率低的热门功能

        Args:
            target_retailer: 目标零售商
            feature_field: 功能字段名（在specs中）
            min_competitors: 最少竞争对手数

        Returns:
            功能Gap列表
        """
        # 统计各零售商的功能覆盖
        feature_by_retailer: dict[str, set[str]] = defaultdict(set)
        for retailer, products in self.retailer_groups.items():
            for p in products:
                specs = p.get("specs", {})
                features = specs.get(feature_field, [])
                if isinstance(features, list):
                    for f in features:
                        feature_by_retailer[retailer].add(str(f).lower().strip())
                elif isinstance(features, str):
                    feature_by_retailer[retailer].add(features.lower().strip())

        target_features = feature_by_retailer.get(target_retailer, set())

        # 统计竞品功能出现频率
        competitor_features: dict[str, set[str]] = defaultdict(set)
        for retailer in self._all_retailers:
            if retailer == target_retailer:
                continue
            for feature in feature_by_retailer.get(retailer, set()):
                competitor_features[feature].add(retailer)

        gaps = []
        for feature, retailers in competitor_features.items():
            if feature not in target_features and len(retailers) >= min_competitors:
                examples = self._get_competitor_examples(
                    feature_field,
                    feature,
                    exclude_retailer=target_retailer,
                )
                priority = min(len(retailers) / len(self._all_retailers) * 5 + 3, 10.0)

                gaps.append(
                    GapOpportunity(
                        gap_type=GapType.FEATURE,
                        target_retailer=target_retailer,
                        dimension=feature_field,
                        dimension_value=feature,
                        competitors_count=len(retailers),
                        competitor_examples=examples,
                        priority_score=round(priority, 1),
                        recommendation=(
                            f"{target_retailer}缺少'{feature}'功能的产品，"
                            f"{len(retailers)}家竞争对手提供该功能"
                        ),
                    )
                )

        return sorted(gaps, key=lambda x: x.priority_score, reverse=True)

    # ──────────────────── 综合分析 ────────────────────

    def analyze_all(
        self,
        target_retailer: str,
        dimensions: Optional[list[str]] = None,
    ) -> dict[str, list[GapOpportunity]]:
        """执行全面的Gap分析

        Args:
            target_retailer: 目标零售商
            dimensions: 要分析的维度列表（用于完全空缺分析）

        Returns:
            按Gap类型分组的分析结果
        """
        if target_retailer not in self.retailer_groups:
            logger.warning(f"目标零售商 {target_retailer} 无数据")
            return {}

        results: dict[str, list[GapOpportunity]] = {}

        # 完全空缺分析
        if dimensions:
            for dim in dimensions:
                gaps = self.find_complete_gaps(target_retailer, dim)
                if gaps:
                    results[f"complete_gap_{dim}"] = gaps
                    logger.info(
                        f"[{target_retailer}] 维度 '{dim}' 发现 {len(gaps)} 个完全空缺"
                    )

        # 品牌空缺
        brand_gaps = self.find_brand_gaps(target_retailer)
        if brand_gaps:
            results["brand_gaps"] = brand_gaps
            logger.info(f"[{target_retailer}] 发现 {len(brand_gaps)} 个品牌空缺")

        # 价格带空缺
        price_gaps = self.find_price_band_gaps(target_retailer)
        if price_gaps:
            results["price_band_gaps"] = price_gaps
            logger.info(f"[{target_retailer}] 发现 {len(price_gaps)} 个价格带空缺")

        # 功能空缺
        feature_gaps = self.find_feature_gaps(target_retailer)
        if feature_gaps:
            results["feature_gaps"] = feature_gaps
            logger.info(f"[{target_retailer}] 发现 {len(feature_gaps)} 个功能空缺")

        return results

    # ──────────────────── 统计摘要 ────────────────────

    def get_coverage_summary(self) -> dict:
        """获取各零售商产品覆盖摘要"""
        summary = {}
        for retailer, products in self.retailer_groups.items():
            prices = [p.get("price", 0) for p in products if p.get("price")]
            ratings = [p.get("rating", 0) for p in products if p.get("rating")]
            brands = set(p.get("brand", "") for p in products if p.get("brand"))

            summary[retailer] = {
                "product_count": len(products),
                "brand_count": len(brands),
                "brands": sorted(brands),
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0,
                    "avg": round(sum(prices) / len(prices), 2) if prices else 0,
                },
                "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0,
                "total_reviews": sum(
                    p.get("review_count", 0) for p in products
                ),
            }
        return summary

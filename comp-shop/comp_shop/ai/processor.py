"""AI处理器 - 封装Claude API调用"""

import json
import logging
from typing import Any, Optional

import anthropic

from ..config import settings
from .prompts import (
    DATA_CLEANING_PROMPT,
    DIMENSION_RECOMMENDATION_PROMPT,
    GAP_ANALYSIS_PROMPT,
    KEYWORD_EXPANSION_PROMPT,
    SPEC_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)


class AIProcessor:
    """AI处理器，基于Claude API进行数据清洗、规格提取、维度推荐和Gap分析"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.claude_model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def _call_claude(self, prompt: str, max_tokens: int = 4096) -> str:
        """调用Claude API"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API调用失败: {e}")
            raise

    def _parse_json_response(self, response: str) -> dict:
        """从Claude响应中解析JSON"""
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试从markdown代码块中提取
        import re

        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找到第一个 { 和最后一个 }
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(response[start : end + 1])
            except json.JSONDecodeError:
                pass

        logger.error(f"无法解析JSON响应: {response[:200]}...")
        raise ValueError("无法从AI响应中解析JSON")

    # ──────────────────── 关键词扩展 ────────────────────

    def expand_keywords(self, keyword: str) -> dict:
        """扩展搜索关键词

        Args:
            keyword: 原始关键词，如 "plier"

        Returns:
            包含扩展关键词列表和子类别的字典
        """
        prompt = KEYWORD_EXPANSION_PROMPT.format(keyword=keyword)
        response = self._call_claude(prompt)
        return self._parse_json_response(response)

    # ──────────────────── 规格提取 ────────────────────

    def extract_specs(
        self,
        name: str,
        brand: str,
        description: str,
        raw_specs: dict,
    ) -> dict:
        """从产品信息中提取结构化规格

        Args:
            name: 产品名称
            brand: 品牌
            description: 产品描述
            raw_specs: 原始规格数据

        Returns:
            结构化规格字典
        """
        prompt = SPEC_EXTRACTION_PROMPT.format(
            name=name,
            brand=brand,
            description=description,
            raw_specs=json.dumps(raw_specs, indent=2) if raw_specs else "N/A",
        )
        response = self._call_claude(prompt)
        return self._parse_json_response(response)

    def batch_extract_specs(self, products: list[dict], batch_size: int = 5) -> list[dict]:
        """批量提取产品规格

        将多个产品合并为一个prompt以减少API调用次数。

        Args:
            products: 产品数据列表
            batch_size: 每批处理的产品数

        Returns:
            提取结果列表，每个元素包含 sku 和 specs
        """
        all_results = []

        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
            batch_prompt = (
                "Extract structured specifications for each of the following products. "
                "Return a JSON array where each element has 'sku' and 'specs' fields.\n\n"
            )

            for j, product in enumerate(batch):
                batch_prompt += f"--- Product {j + 1} (SKU: {product.get('sku', 'N/A')}) ---\n"
                batch_prompt += SPEC_EXTRACTION_PROMPT.format(
                    name=product.get("name", ""),
                    brand=product.get("brand", ""),
                    description=product.get("description", ""),
                    raw_specs=json.dumps(product.get("specs", {}), indent=2),
                )
                batch_prompt += "\n\n"

            batch_prompt += (
                "\nReturn the results as a JSON array: "
                '[{"sku": "...", "specs": {...}}, ...]'
            )

            try:
                response = self._call_claude(batch_prompt, max_tokens=8192)
                result = self._parse_json_response(response)
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, dict) and "results" in result:
                    all_results.extend(result["results"])
            except Exception as e:
                logger.error(f"批量规格提取失败 (batch {i // batch_size}): {e}")
                # 降级为逐个处理
                for product in batch:
                    try:
                        specs = self.extract_specs(
                            name=product.get("name", ""),
                            brand=product.get("brand", ""),
                            description=product.get("description", ""),
                            raw_specs=product.get("specs", {}),
                        )
                        all_results.append({"sku": product.get("sku", ""), "specs": specs})
                    except Exception as inner_e:
                        logger.error(f"单个规格提取失败 (SKU: {product.get('sku')}): {inner_e}")

        return all_results

    # ──────────────────── 维度推荐 ────────────────────

    def recommend_dimensions(
        self,
        category: str,
        product_count: int,
        retailers: list[str],
        field_distributions: dict[str, Any],
        sample_names: list[str],
    ) -> dict:
        """推荐分析维度

        Args:
            category: 品类名称
            product_count: 产品总数
            retailers: 零售商列表
            field_distributions: 字段值分布统计
            sample_names: 产品名称样本

        Returns:
            推荐维度和矩阵布局建议
        """
        prompt = DIMENSION_RECOMMENDATION_PROMPT.format(
            category=category,
            product_count=product_count,
            retailers=", ".join(retailers),
            field_distributions=json.dumps(field_distributions, indent=2),
            sample_names="\n".join(f"- {name}" for name in sample_names[:20]),
        )
        response = self._call_claude(prompt)
        return self._parse_json_response(response)

    # ──────────────────── Gap分析 ────────────────────

    def analyze_gaps(
        self,
        target_retailer: str,
        category: str,
        coverage_data: str,
        gap_data: str,
        price_analysis: str,
    ) -> dict:
        """AI辅助Gap分析

        Args:
            target_retailer: 目标零售商
            category: 品类
            coverage_data: 各零售商产品覆盖数据
            gap_data: 初步Gap数据
            price_analysis: 价格区间分析

        Returns:
            详细的Gap分析结果和建议
        """
        prompt = GAP_ANALYSIS_PROMPT.format(
            target_retailer=target_retailer,
            category=category,
            coverage_data=coverage_data,
            gap_data=gap_data,
            price_analysis=price_analysis,
        )
        response = self._call_claude(prompt, max_tokens=8192)
        return self._parse_json_response(response)

    # ──────────────────── 数据清洗 ────────────────────

    def clean_data(self, products: list[dict]) -> dict:
        """AI辅助数据清洗

        Args:
            products: 产品数据列表（最多20个产品一批）

        Returns:
            清洗建议和修正列表
        """
        prompt = DATA_CLEANING_PROMPT.format(
            products_json=json.dumps(products[:20], indent=2, ensure_ascii=False)
        )
        response = self._call_claude(prompt)
        return self._parse_json_response(response)

"""飞书集成模块 - 消息通知和设计需求推送"""

import logging
from typing import Any, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class FeishuBot:
    """飞书机器人集成

    功能：
    - 发送任务完成通知
    - 推送Gap分析报告摘要
    - 发送设计需求到设计部门群
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or settings.feishu_webhook_url

    async def _send_message(self, payload: dict) -> bool:
        """发送消息到飞书webhook"""
        if not self.webhook_url:
            logger.warning("飞书Webhook URL未配置，跳过通知")
            return False

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10,
                )
                resp.raise_for_status()
                result = resp.json()
                if result.get("code") != 0:
                    logger.error(f"飞书消息发送失败: {result}")
                    return False
                return True
        except Exception as e:
            logger.error(f"飞书消息发送异常: {e}")
            return False

    async def send_task_started(self, task_id: int, category: str, retailers: list[str]):
        """发送任务开始通知"""
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"COMP Shop 采集任务 #{task_id} 已启动",
                    },
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**品类**: {category}\n"
                                f"**零售商**: {', '.join(retailers)}\n"
                                f"**状态**: 采集中..."
                            ),
                        },
                    },
                ],
            },
        }
        return await self._send_message(payload)

    async def send_task_completed(
        self,
        task_id: int,
        category: str,
        results: dict[str, Any],
        report_url: Optional[str] = None,
    ):
        """发送任务完成通知"""
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**品类**: {category}\n"
                        f"**采集产品数**: {results.get('product_count', 0)}\n"
                        f"**发现Gap数**: {results.get('gap_count', 0)}\n"
                        f"**耗时**: {results.get('duration', 'N/A')}"
                    ),
                },
            },
        ]

        # 添加各零售商统计
        retailer_stats = results.get("retailer_stats", {})
        if retailer_stats:
            stats_lines = []
            for retailer, count in retailer_stats.items():
                stats_lines.append(f"  - {retailer}: {count} 个产品")
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**各零售商数据**:\n" + "\n".join(stats_lines),
                    },
                }
            )

        # 报告链接按钮
        if report_url:
            elements.append(
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看报告"},
                            "url": report_url,
                            "type": "primary",
                        },
                    ],
                }
            )

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"COMP Shop 任务 #{task_id} 采集完成",
                    },
                    "template": "green",
                },
                "elements": elements,
            },
        }
        return await self._send_message(payload)

    async def send_task_failed(
        self,
        task_id: int,
        category: str,
        error: str,
    ):
        """发送任务失败通知"""
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"COMP Shop 任务 #{task_id} 采集失败",
                    },
                    "template": "red",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**品类**: {category}\n"
                                f"**错误信息**: {error[:500]}"
                            ),
                        },
                    },
                ],
            },
        }
        return await self._send_message(payload)

    async def send_gap_report(
        self,
        task_id: int,
        target_retailer: str,
        top_gaps: list[dict],
        summary: str,
    ):
        """发送Gap分析报告摘要"""
        gap_lines = []
        for i, gap in enumerate(top_gaps[:5], 1):
            priority = gap.get("priority_score", 0)
            value = gap.get("dimension_value", "N/A")
            gap_type = gap.get("gap_type", "unknown")
            gap_lines.append(
                f"{i}. [{priority:.1f}分] {gap_type}: {value}"
            )

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**目标零售商**: {target_retailer}\n"
                        f"**分析摘要**: {summary}\n\n"
                        f"**Top 5 市场机会**:\n" + "\n".join(gap_lines)
                    ),
                },
            },
        ]

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"Gap分析报告 - 任务 #{task_id}",
                    },
                    "template": "orange",
                },
                "elements": elements,
            },
        }
        return await self._send_message(payload)

    async def send_design_request(
        self,
        products: list[dict],
        category: str,
        target_retailer: str,
    ):
        """推送产品设计需求到设计部门群"""
        product_lines = []
        for p in products[:10]:
            product_lines.append(
                f"- {p.get('name', 'N/A')} | "
                f"建议零售价: ${p.get('suggested_price', 0):.2f} | "
                f"规格: {p.get('specs_summary', 'N/A')}"
            )

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"新产品设计需求 - {category} ({target_retailer})",
                    },
                    "template": "purple",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**品类**: {category}\n"
                                f"**目标零售商**: {target_retailer}\n"
                                f"**产品数量**: {len(products)}\n\n"
                                f"**产品清单**:\n" + "\n".join(product_lines)
                            ),
                        },
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "请设计团队根据以上清单准备产品效果图和Sell Sheet",
                            },
                        ],
                    },
                ],
            },
        }
        return await self._send_message(payload)

"""采集任务执行器 - 协调爬虫、AI处理和数据存储"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional

from ..analysis.gap_analyzer import GapAnalyzer
from ..config import settings
from ..integrations.feishu import FeishuBot
from ..models import GapAnalysis, Product, ProductSpec, ScrapeTask, SessionLocal
from ..scrapers import get_scraper
from ..scrapers.base import Product as ProductData

logger = logging.getLogger(__name__)


async def _scrape_retailer(
    retailer: str,
    keywords: list[str],
    in_store_only: bool,
) -> list[ProductData]:
    """采集单个零售商的数据"""
    scraper = get_scraper(retailer)
    try:
        products = await scraper.search_multiple_keywords(
            keywords=keywords,
            in_store_only=in_store_only,
            max_pages=10,
        )
        logger.info(f"[{retailer}] 采集完成，获得 {len(products)} 个产品")
        return products
    except Exception as e:
        logger.error(f"[{retailer}] 采集失败: {e}")
        return []
    finally:
        await scraper.close()


def _update_task_progress(
    task_id: int,
    retailer: str,
    status: str,
    count: int = 0,
):
    """更新任务进度"""
    db = SessionLocal()
    try:
        task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
        if task:
            progress = task.progress or {}
            progress[retailer] = {"status": status, "count": count}
            task.progress = progress
            # 需要显式标记为modified，因为JSON列不会自动检测变化
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(task, "progress")
            db.commit()
    finally:
        db.close()


def _save_products(
    task_id: int,
    products: list[ProductData],
) -> int:
    """将产品数据保存到数据库"""
    db = SessionLocal()
    saved = 0
    try:
        for p in products:
            existing = (
                db.query(Product)
                .filter(Product.sku == p.sku, Product.retailer == p.retailer)
                .first()
            )
            if existing:
                # 更新现有记录
                existing.name = p.name
                existing.brand = p.brand
                existing.price = p.price
                existing.rating = p.rating
                existing.review_count = p.review_count
                existing.description = p.description
                existing.product_url = p.product_url
                existing.in_store_only = p.in_store_only
                existing.image_urls = p.image_urls
                existing.raw_specs = p.specs
                existing.task_id = task_id
                existing.updated_at = datetime.utcnow()
            else:
                db_product = Product(
                    sku=p.sku,
                    retailer=p.retailer,
                    name=p.name,
                    brand=p.brand,
                    price=p.price,
                    rating=p.rating,
                    review_count=p.review_count,
                    description=p.description,
                    product_url=p.product_url,
                    in_store_only=p.in_store_only,
                    image_urls=p.image_urls,
                    raw_specs=p.specs,
                    task_id=task_id,
                )
                db.add(db_product)
            saved += 1

        db.commit()
    except Exception as e:
        logger.error(f"保存产品数据失败: {e}")
        db.rollback()
    finally:
        db.close()

    return saved


def _run_gap_analysis(task_id: int, target_retailers: Optional[list[str]] = None):
    """对任务数据执行Gap分析"""
    db = SessionLocal()
    try:
        products = db.query(Product).filter(Product.task_id == task_id).all()
        if not products:
            return

        product_dicts = [
            {
                "sku": p.sku,
                "name": p.name,
                "brand": p.brand,
                "price": p.price,
                "rating": p.rating,
                "review_count": p.review_count,
                "retailer": p.retailer,
                "in_store_only": p.in_store_only,
                "specs": p.raw_specs or {},
            }
            for p in products
        ]

        analyzer = GapAnalyzer(product_dicts)
        retailers = target_retailers or list(analyzer.retailer_groups.keys())

        for target in retailers:
            results = analyzer.analyze_all(target, dimensions=["size", "type"])

            # 清除旧结果
            db.query(GapAnalysis).filter(
                GapAnalysis.task_id == task_id,
                GapAnalysis.target_retailer == target,
            ).delete()

            # 保存新结果
            for category, gaps in results.items():
                for gap in gaps:
                    db_gap = GapAnalysis(
                        task_id=task_id,
                        target_retailer=target,
                        gap_type=gap.gap_type.value,
                        dimension=gap.dimension,
                        dimension_value=gap.dimension_value,
                        competitors_count=gap.competitors_count,
                        competitor_examples=gap.competitor_examples,
                        priority_score=gap.priority_score,
                        recommendation=gap.recommendation,
                    )
                    db.add(db_gap)

            db.commit()
            logger.info(f"Gap分析完成: 目标={target}")

    except Exception as e:
        logger.error(f"Gap分析失败: {e}")
        db.rollback()
    finally:
        db.close()


async def _execute_scrape_task(task_id: int):
    """异步执行采集任务的核心逻辑"""
    db = SessionLocal()
    feishu = FeishuBot()

    try:
        task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
        if not task:
            logger.error(f"任务 #{task_id} 不存在")
            return

        # 更新任务状态
        task.status = "running"
        task.started_at = datetime.utcnow()
        db.commit()

        keywords = task.keywords or [task.category]
        retailers = task.retailers or ["homedepot", "walmart", "lowes", "harborfreight"]

        # 通知飞书
        await feishu.send_task_started(task_id, task.category, retailers)

        start_time = time.time()
        total_products = 0
        retailer_stats = {}

        # 如果没有提供关键词，尝试用AI扩展
        if len(keywords) == 1 and settings.anthropic_api_key:
            try:
                from ..ai.processor import AIProcessor

                ai = AIProcessor()
                expanded = ai.expand_keywords(keywords[0])
                keywords = [expanded.get("primary_keyword", keywords[0])]
                keywords.extend(expanded.get("expanded_keywords", [])[:5])
                logger.info(f"关键词已扩展: {keywords}")
            except Exception as e:
                logger.warning(f"关键词扩展失败，使用原始关键词: {e}")

        # 并行采集各零售商（但控制并发数）
        for retailer in retailers:
            if task.status == "cancelled":
                logger.info(f"任务 #{task_id} 已取消，停止采集")
                break

            _update_task_progress(task_id, retailer, "running")

            try:
                products = await _scrape_retailer(
                    retailer=retailer,
                    keywords=keywords,
                    in_store_only=task.in_store_only,
                )

                # 保存到数据库
                saved = _save_products(task_id, products)
                total_products += saved
                retailer_stats[retailer] = saved

                _update_task_progress(task_id, retailer, "completed", saved)
                logger.info(f"[{retailer}] 保存 {saved} 个产品")

            except Exception as e:
                logger.error(f"[{retailer}] 采集异常: {e}")
                _update_task_progress(task_id, retailer, "failed")
                retailer_stats[retailer] = 0

        # 执行Gap分析
        if total_products > 0:
            _run_gap_analysis(task_id)

        # 更新任务最终状态
        duration = time.time() - start_time
        task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
        if task and task.status != "cancelled":
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.product_count = total_products
            db.commit()

            # 统计Gap数量
            gap_count = (
                db.query(GapAnalysis).filter(GapAnalysis.task_id == task_id).count()
            )

            # 通知飞书
            await feishu.send_task_completed(
                task_id=task_id,
                category=task.category,
                results={
                    "product_count": total_products,
                    "gap_count": gap_count,
                    "duration": f"{duration / 60:.1f} 分钟",
                    "retailer_stats": retailer_stats,
                },
            )

            logger.info(
                f"任务 #{task_id} 完成: "
                f"{total_products} 产品, {gap_count} gaps, "
                f"耗时 {duration:.0f}s"
            )

    except Exception as e:
        logger.error(f"任务 #{task_id} 执行异常: {e}")
        task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_message = str(e)[:1000]
            db.commit()

        await feishu.send_task_failed(task_id, task.category if task else "unknown", str(e))

    finally:
        db.close()


def run_scrape_task(task_id: int):
    """同步入口，在后台线程中运行异步任务"""
    asyncio.run(_execute_scrape_task(task_id))

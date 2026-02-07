"""命令行入口 - COMP Shop数据采集自动化"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .config import settings


def setup_logging(level: str = "INFO"):
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_serve(args):
    """启动API服务"""
    import uvicorn

    from .api.app import app
    from .models import init_db

    init_db()
    uvicorn.run(
        app,
        host=args.host or settings.api_host,
        port=args.port or settings.api_port,
        reload=args.reload,
    )


def cmd_scrape(args):
    """执行数据采集"""

    async def _run():
        from .scrapers import get_scraper

        retailer = args.retailer
        keywords = args.keywords.split(",")
        in_store_only = not args.no_in_store_filter

        scraper = get_scraper(retailer)
        try:
            products = await scraper.search_multiple_keywords(
                keywords=keywords,
                in_store_only=in_store_only,
                max_pages=args.max_pages,
            )
            print(f"\n采集完成: {len(products)} 个产品")
            for p in products[:10]:
                print(
                    f"  [{p.sku}] {p.brand} - {p.name} | "
                    f"${p.price:.2f} | Rating: {p.rating} | "
                    f"Reviews: {p.review_count}"
                )
            if len(products) > 10:
                print(f"  ... 还有 {len(products) - 10} 个产品")

            # 保存到Excel
            if args.output:
                from .export.excel import ExcelExporter

                exporter = ExcelExporter(args.output)
                product_dicts = [p.to_dict() for p in products]
                exporter.add_raw_data_sheets({retailer: product_dicts})
                filepath = exporter.save()
                print(f"\n已导出到: {filepath}")

        finally:
            await scraper.close()

    asyncio.run(_run())


def cmd_analyze(args):
    """执行Gap分析"""
    from .analysis.gap_analyzer import GapAnalyzer
    from .models import Product, SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        query = db.query(Product)
        if args.task_id:
            query = query.filter(Product.task_id == args.task_id)

        products = query.all()
        if not products:
            print("没有找到产品数据")
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
                "specs": p.raw_specs or {},
            }
            for p in products
        ]

        analyzer = GapAnalyzer(product_dicts)

        # 打印覆盖摘要
        summary = analyzer.get_coverage_summary()
        print("\n=== 零售商覆盖摘要 ===")
        for retailer, data in summary.items():
            print(
                f"  {retailer}: {data['product_count']} 产品, "
                f"{data['brand_count']} 品牌, "
                f"价格 ${data['price_range']['min']:.2f}-"
                f"${data['price_range']['max']:.2f}, "
                f"平均评分 {data['avg_rating']}"
            )

        # 执行Gap分析
        target = args.target
        results = analyzer.analyze_all(target, dimensions=args.dimensions.split(","))

        print(f"\n=== Gap分析: {target} ===")
        total_gaps = 0
        for category, gaps in results.items():
            print(f"\n  [{category}] 发现 {len(gaps)} 个Gap:")
            for gap in gaps[:5]:
                print(
                    f"    [{gap.priority_score:.1f}] {gap.dimension}={gap.dimension_value} "
                    f"(竞争对手: {gap.competitors_count}家)"
                )
                print(f"        建议: {gap.recommendation}")
            total_gaps += len(gaps)

        print(f"\n总计发现 {total_gaps} 个市场空缺")

        # 导出Excel
        if args.output:
            from .export.excel import export_full_report

            all_gaps = []
            for gaps in results.values():
                all_gaps.extend(g.to_dict() for g in gaps)

            filepath = export_full_report(
                products=product_dicts,
                gaps=all_gaps,
                summary=summary,
                primary_dimension=args.dimensions.split(",")[0],
                output_path=args.output,
            )
            print(f"\n报告已导出到: {filepath}")

    finally:
        db.close()


def cmd_init_db(args):
    """初始化数据库"""
    from .models import init_db

    init_db()
    print("数据库初始化完成")


def cmd_expand_keywords(args):
    """AI关键词扩展"""
    from .ai.processor import AIProcessor

    ai = AIProcessor()
    result = ai.expand_keywords(args.keyword)

    print(f"\n关键词扩展: {args.keyword}")
    print(f"  主关键词: {result.get('primary_keyword', '')}")
    print(f"  扩展关键词:")
    for kw in result.get("expanded_keywords", []):
        print(f"    - {kw}")
    print(f"  子类别:")
    for cat in result.get("subcategories", []):
        print(f"    - {cat}")
    if result.get("notes"):
        print(f"  备注: {result['notes']}")


def main():
    parser = argparse.ArgumentParser(
        prog="comp-shop",
        description="COMP Shop 数据采集自动化系统 - 市场部竞品数据采集与Gap分析",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # serve - 启动API服务
    serve_parser = subparsers.add_parser("serve", help="启动API服务")
    serve_parser.add_argument("--host", default=None, help="绑定地址")
    serve_parser.add_argument("--port", type=int, default=None, help="端口")
    serve_parser.add_argument("--reload", action="store_true", help="开发模式热重载")

    # scrape - 执行数据采集
    scrape_parser = subparsers.add_parser("scrape", help="执行数据采集")
    scrape_parser.add_argument("retailer", help="零售商 (homedepot/walmart/lowes/harborfreight)")
    scrape_parser.add_argument("keywords", help="搜索关键词，逗号分隔")
    scrape_parser.add_argument("--max-pages", type=int, default=5, help="最大翻页数")
    scrape_parser.add_argument("--no-in-store-filter", action="store_true", help="不筛选In-Store Only")
    scrape_parser.add_argument("-o", "--output", help="输出Excel文件路径")

    # analyze - Gap分析
    analyze_parser = subparsers.add_parser("analyze", help="执行Gap分析")
    analyze_parser.add_argument("target", help="目标零售商")
    analyze_parser.add_argument("--task-id", type=int, help="任务ID（不指定则分析全部数据）")
    analyze_parser.add_argument("--dimensions", default="size,type", help="分析维度，逗号分隔")
    analyze_parser.add_argument("-o", "--output", help="输出Excel报告路径")

    # init-db - 初始化数据库
    subparsers.add_parser("init-db", help="初始化数据库")

    # expand-keywords - AI关键词扩展
    kw_parser = subparsers.add_parser("expand-keywords", help="AI关键词扩展")
    kw_parser.add_argument("keyword", help="原始关键词")

    args = parser.parse_args()
    setup_logging(args.log_level)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "serve": cmd_serve,
        "scrape": cmd_scrape,
        "analyze": cmd_analyze,
        "init-db": cmd_init_db,
        "expand-keywords": cmd_expand_keywords,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

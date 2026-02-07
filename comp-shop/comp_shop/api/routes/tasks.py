"""采集任务管理API"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...models import Product, ScrapeTask, SessionLocal, get_db
from ...tasks.scrape import run_scrape_task

logger = logging.getLogger(__name__)
router = APIRouter()


# ──────────────────── 请求/响应模型 ────────────────────


class CreateTaskRequest(BaseModel):
    category: str = Field(..., description="品类名称，如 plier")
    retailers: list[str] = Field(
        default=["homedepot", "walmart", "lowes", "harborfreight"],
        description="目标零售商列表",
    )
    keywords: list[str] = Field(
        default=[],
        description="自定义搜索关键词（为空则自动扩展）",
    )
    in_store_only: bool = Field(default=True, description="是否仅筛选店内销售")
    created_by: str = Field(default="system", description="创建人")


class TaskResponse(BaseModel):
    task_id: int
    category: str
    status: str
    retailers: list[str]
    product_count: int
    progress: dict
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int


class ProductResponse(BaseModel):
    sku: str
    name: str
    brand: str
    price: float
    rating: Optional[float]
    review_count: int
    retailer: str
    in_store_only: bool
    product_url: str
    image_urls: list[str]
    specs: dict

    class Config:
        from_attributes = True


# ──────────────────── 路由处理函数 ────────────────────


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(_get_db),
):
    """创建新的采集任务"""
    task = ScrapeTask(
        category=request.category,
        keywords=request.keywords,
        retailers=request.retailers,
        in_store_only=request.in_store_only,
        status="pending",
        progress={r: {"status": "pending", "count": 0} for r in request.retailers},
        created_by=request.created_by,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 后台启动采集任务
    background_tasks.add_task(run_scrape_task, task.id)

    logger.info(f"创建采集任务 #{task.id}: {request.category}, 零售商: {request.retailers}")

    return TaskResponse(
        task_id=task.id,
        category=task.category,
        status=task.status,
        retailers=task.retailers or [],
        product_count=task.product_count,
        progress=task.progress or {},
        created_at=task.created_at.isoformat() if task.created_at else None,
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(_get_db),
):
    """查询任务列表"""
    query = db.query(ScrapeTask)
    if status:
        query = query.filter(ScrapeTask.status == status)

    total = query.count()
    tasks = (
        query.order_by(ScrapeTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TaskListResponse(
        items=[
            TaskResponse(
                task_id=t.id,
                category=t.category,
                status=t.status,
                retailers=t.retailers or [],
                product_count=t.product_count,
                progress=t.progress or {},
                created_at=t.created_at.isoformat() if t.created_at else None,
                started_at=t.started_at.isoformat() if t.started_at else None,
                completed_at=t.completed_at.isoformat() if t.completed_at else None,
                error_message=t.error_message,
            )
            for t in tasks
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(_get_db)):
    """查询任务详情"""
    task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")

    return TaskResponse(
        task_id=task.id,
        category=task.category,
        status=task.status,
        retailers=task.retailers or [],
        product_count=task.product_count,
        progress=task.progress or {},
        created_at=task.created_at.isoformat() if task.created_at else None,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        error_message=task.error_message,
    )


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int, db: Session = Depends(_get_db)):
    """取消采集任务"""
    task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")
    if task.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"任务状态 {task.status} 不可取消")

    task.status = "cancelled"
    db.commit()
    return {"message": f"任务 #{task_id} 已取消"}


@router.get("/{task_id}/products", response_model=list[ProductResponse])
async def get_task_products(
    task_id: int,
    retailer: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(_get_db),
):
    """获取任务的产品数据"""
    task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")

    query = db.query(Product).filter(Product.task_id == task_id)
    if retailer:
        query = query.filter(Product.retailer == retailer)

    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return [
        ProductResponse(
            sku=p.sku,
            name=p.name or "",
            brand=p.brand or "",
            price=p.price or 0,
            rating=p.rating,
            review_count=p.review_count or 0,
            retailer=p.retailer,
            in_store_only=p.in_store_only or False,
            product_url=p.product_url or "",
            image_urls=p.image_urls or [],
            specs=p.raw_specs or {},
        )
        for p in products
    ]


@router.post("/{task_id}/export")
async def export_task(task_id: int, db: Session = Depends(_get_db)):
    """导出任务数据为Excel"""
    from collections import defaultdict
    from pathlib import Path

    from ...analysis.gap_analyzer import GapAnalyzer
    from ...export.excel import export_full_report

    task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成，无法导出")

    products = db.query(Product).filter(Product.task_id == task_id).all()
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
            "product_url": p.product_url,
            "image_urls": p.image_urls or [],
            "specs": p.raw_specs or {},
        }
        for p in products
    ]

    analyzer = GapAnalyzer(product_dicts)
    summary = analyzer.get_coverage_summary()

    # 对每个零售商进行Gap分析
    all_gaps = []
    retailers = list(set(p.retailer for p in products))
    for target in retailers:
        gaps = analyzer.find_complete_gaps(target, "size")
        gaps.extend(analyzer.find_brand_gaps(target))
        gaps.extend(analyzer.find_price_band_gaps(target))
        all_gaps.extend(g.to_dict() for g in gaps)

    output_dir = Path("./data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"comp_shop_task_{task_id}_{task.category}.xlsx"

    filepath = export_full_report(
        products=product_dicts,
        gaps=all_gaps,
        summary=summary,
        primary_dimension="size",
        output_path=output_path,
        primary_label="Size",
    )

    return {"message": "导出成功", "file_path": filepath}

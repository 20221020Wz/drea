"""Gap分析API"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...models import GapAnalysis, Product, ScrapeTask, SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()


class GapResponse(BaseModel):
    id: int
    task_id: int
    target_retailer: str
    gap_type: str
    dimension: Optional[str]
    dimension_value: Optional[str]
    competitors_count: int
    competitor_examples: list[str]
    priority_score: float
    recommendation: Optional[str]

    class Config:
        from_attributes = True


class GapListResponse(BaseModel):
    task_id: int
    target_retailer: str
    gaps: list[GapResponse]
    total_gaps: int


class RunGapAnalysisRequest(BaseModel):
    task_id: int = Field(..., description="采集任务ID")
    target_retailer: str = Field(..., description="目标零售商")
    dimensions: list[str] = Field(
        default=["size", "type"],
        description="分析维度列表",
    )


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{task_id}", response_model=GapListResponse)
async def get_gaps(
    task_id: int,
    target: str = Query(..., description="目标零售商"),
    gap_type: Optional[str] = Query(default=None),
    min_priority: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(_get_db),
):
    """获取Gap分析结果"""
    task = db.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")

    query = (
        db.query(GapAnalysis)
        .filter(GapAnalysis.task_id == task_id)
        .filter(GapAnalysis.target_retailer == target)
    )

    if gap_type:
        query = query.filter(GapAnalysis.gap_type == gap_type)

    if min_priority > 0:
        query = query.filter(GapAnalysis.priority_score >= min_priority)

    gaps = (
        query.order_by(GapAnalysis.priority_score.desc()).limit(limit).all()
    )

    return GapListResponse(
        task_id=task_id,
        target_retailer=target,
        gaps=[
            GapResponse(
                id=g.id,
                task_id=g.task_id,
                target_retailer=g.target_retailer,
                gap_type=g.gap_type,
                dimension=g.dimension,
                dimension_value=g.dimension_value,
                competitors_count=g.competitors_count,
                competitor_examples=g.competitor_examples or [],
                priority_score=g.priority_score,
                recommendation=g.recommendation,
            )
            for g in gaps
        ],
        total_gaps=len(gaps),
    )


@router.post("/analyze")
async def run_gap_analysis(
    request: RunGapAnalysisRequest,
    db: Session = Depends(_get_db),
):
    """执行Gap分析"""
    from ...analysis.gap_analyzer import GapAnalyzer

    task = db.query(ScrapeTask).filter(ScrapeTask.id == request.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 #{request.task_id} 不存在")

    products = db.query(Product).filter(Product.task_id == request.task_id).all()
    if not products:
        raise HTTPException(status_code=400, detail="任务尚无产品数据")

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
    results = analyzer.analyze_all(request.target_retailer, request.dimensions)

    # 清除旧的分析结果
    db.query(GapAnalysis).filter(
        GapAnalysis.task_id == request.task_id,
        GapAnalysis.target_retailer == request.target_retailer,
    ).delete()

    # 保存新结果
    saved_count = 0
    for gap_category, gaps in results.items():
        for gap in gaps:
            db_gap = GapAnalysis(
                task_id=request.task_id,
                target_retailer=request.target_retailer,
                gap_type=gap.gap_type.value,
                dimension=gap.dimension,
                dimension_value=gap.dimension_value,
                competitors_count=gap.competitors_count,
                competitor_examples=gap.competitor_examples,
                priority_score=gap.priority_score,
                recommendation=gap.recommendation,
            )
            db.add(db_gap)
            saved_count += 1

    db.commit()
    summary = analyzer.get_coverage_summary()

    logger.info(
        f"Gap分析完成: 任务#{request.task_id}, "
        f"目标={request.target_retailer}, 发现{saved_count}个Gap"
    )

    return {
        "message": f"Gap分析完成，发现 {saved_count} 个市场空缺",
        "task_id": request.task_id,
        "target_retailer": request.target_retailer,
        "gap_count": saved_count,
        "coverage_summary": summary,
    }

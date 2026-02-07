"""FastAPI应用入口"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..models import init_db
from .routes import gaps, tasks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("COMP Shop API 启动中...")
    init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("COMP Shop API 关闭")


app = FastAPI(
    title="COMP Shop 数据采集自动化系统",
    description="市场部竞品数据采集、AI分析与Gap识别平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(gaps.router, prefix="/api/gaps", tags=["Gap Analysis"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "comp-shop"}


@app.get("/api/stats")
async def get_stats():
    """获取系统统计信息"""
    from sqlalchemy import func

    from ..models import GapAnalysis, Product, ScrapeTask, SessionLocal

    db = SessionLocal()
    try:
        task_count = db.query(func.count(ScrapeTask.id)).scalar()
        product_count = db.query(func.count(Product.id)).scalar()
        gap_count = db.query(func.count(GapAnalysis.id)).scalar()
        running_tasks = (
            db.query(func.count(ScrapeTask.id))
            .filter(ScrapeTask.status == "running")
            .scalar()
        )
        return {
            "total_tasks": task_count,
            "running_tasks": running_tasks,
            "total_products": product_count,
            "total_gaps": gap_count,
        }
    finally:
        db.close()

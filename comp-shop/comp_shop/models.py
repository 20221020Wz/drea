"""数据库模型定义 - SQLAlchemy ORM"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


# ──────────────────── 枚举类型 ────────────────────


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RetailerName(str, PyEnum):
    HOMEDEPOT = "homedepot"
    WALMART = "walmart"
    LOWES = "lowes"
    HARBORFREIGHT = "harborfreight"


class GapType(str, PyEnum):
    COMPLETE = "complete_gap"
    BRAND = "brand_gap"
    PRICE_BAND = "price_band_gap"
    FEATURE = "feature_gap"


# ──────────────────── 产品表 ────────────────────


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("sku", "retailer", name="uq_sku_retailer"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(50), nullable=False, index=True)
    retailer = Column(String(50), nullable=False, index=True)
    name = Column(String(500))
    brand = Column(String(100), index=True)
    price = Column(Float)
    rating = Column(Float)
    review_count = Column(Integer, default=0)
    description = Column(Text)
    product_url = Column(String(1000))
    in_store_only = Column(Boolean, default=False)
    image_urls = Column(JSON, default=list)
    raw_specs = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    task_id = Column(Integer, ForeignKey("scrape_tasks.id"), nullable=True)
    specs = relationship("ProductSpec", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(sku={self.sku}, retailer={self.retailer}, name={self.name!r})>"


# ──────────────────── 产品规格表 (AI提取后) ────────────────────


class ProductSpec(Base):
    __tablename__ = "product_specs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    spec_key = Column(String(100), nullable=False)
    spec_value = Column(String(500))
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="specs")

    def __repr__(self):
        return f"<ProductSpec({self.spec_key}={self.spec_value})>"


# ──────────────────── 采集任务表 ────────────────────


class ScrapeTask(Base):
    __tablename__ = "scrape_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False)
    keywords = Column(JSON, default=list)
    retailers = Column(JSON, default=list)
    in_store_only = Column(Boolean, default=True)
    status = Column(String(20), default=TaskStatus.PENDING.value)
    progress = Column(JSON, default=dict)
    product_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    products = relationship("Product", backref="task", lazy="dynamic")
    gap_results = relationship("GapAnalysis", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScrapeTask(id={self.id}, category={self.category}, status={self.status})>"


# ──────────────────── Gap分析结果表 ────────────────────


class GapAnalysis(Base):
    __tablename__ = "gap_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("scrape_tasks.id", ondelete="CASCADE"), nullable=False)
    target_retailer = Column(String(50), nullable=False)
    gap_type = Column(String(50), nullable=False)
    dimension = Column(String(100))
    dimension_value = Column(String(200))
    competitors_count = Column(Integer, default=0)
    competitor_examples = Column(JSON, default=list)
    priority_score = Column(Float, default=0.0)
    recommendation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("ScrapeTask", back_populates="gap_results")

    def __repr__(self):
        return (
            f"<GapAnalysis(type={self.gap_type}, "
            f"retailer={self.target_retailer}, "
            f"value={self.dimension_value})>"
        )


# ──────────────────── 数据库引擎和会话 ────────────────────


engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """获取数据库会话（用于FastAPI依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

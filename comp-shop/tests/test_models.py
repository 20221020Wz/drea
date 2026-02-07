"""数据模型测试"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from comp_shop.models import (
    Base,
    GapAnalysis,
    Product,
    ProductSpec,
    ScrapeTask,
)


@pytest.fixture
def db_session():
    """创建内存数据库用于测试"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestProduct:
    def test_create_product(self, db_session):
        product = Product(
            sku="TEST001",
            retailer="homedepot",
            name="Test Pliers",
            brand="TestBrand",
            price=19.99,
            rating=4.5,
            review_count=100,
        )
        db_session.add(product)
        db_session.commit()

        result = db_session.query(Product).filter_by(sku="TEST001").first()
        assert result is not None
        assert result.name == "Test Pliers"
        assert result.price == 19.99

    def test_unique_constraint(self, db_session):
        p1 = Product(sku="SKU001", retailer="homedepot", name="Product 1")
        p2 = Product(sku="SKU001", retailer="homedepot", name="Product 2")
        db_session.add(p1)
        db_session.commit()

        db_session.add(p2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
        db_session.rollback()

    def test_same_sku_different_retailer(self, db_session):
        p1 = Product(sku="SKU001", retailer="homedepot", name="HD Product")
        p2 = Product(sku="SKU001", retailer="walmart", name="WM Product")
        db_session.add_all([p1, p2])
        db_session.commit()

        count = db_session.query(Product).filter_by(sku="SKU001").count()
        assert count == 2


class TestProductSpec:
    def test_create_spec(self, db_session):
        product = Product(sku="P001", retailer="walmart", name="Test")
        db_session.add(product)
        db_session.commit()

        spec = ProductSpec(
            product_id=product.id,
            spec_key="size",
            spec_value="8 in.",
            confidence=0.95,
        )
        db_session.add(spec)
        db_session.commit()

        result = db_session.query(ProductSpec).filter_by(product_id=product.id).first()
        assert result.spec_key == "size"
        assert result.confidence == 0.95

    def test_cascade_delete(self, db_session):
        product = Product(sku="P002", retailer="lowes", name="Test")
        db_session.add(product)
        db_session.commit()

        spec = ProductSpec(
            product_id=product.id,
            spec_key="type",
            spec_value="Needle Nose",
        )
        db_session.add(spec)
        db_session.commit()

        db_session.delete(product)
        db_session.commit()

        count = db_session.query(ProductSpec).count()
        assert count == 0


class TestScrapeTask:
    def test_create_task(self, db_session):
        task = ScrapeTask(
            category="plier",
            keywords=["plier", "pliers"],
            retailers=["homedepot", "walmart"],
            in_store_only=True,
            status="pending",
        )
        db_session.add(task)
        db_session.commit()

        result = db_session.query(ScrapeTask).first()
        assert result.category == "plier"
        assert result.retailers == ["homedepot", "walmart"]
        assert result.status == "pending"

    def test_task_progress(self, db_session):
        task = ScrapeTask(
            category="wrench",
            progress={"homedepot": {"status": "running", "count": 50}},
        )
        db_session.add(task)
        db_session.commit()

        result = db_session.query(ScrapeTask).first()
        assert result.progress["homedepot"]["count"] == 50


class TestGapAnalysis:
    def test_create_gap(self, db_session):
        task = ScrapeTask(category="plier")
        db_session.add(task)
        db_session.commit()

        gap = GapAnalysis(
            task_id=task.id,
            target_retailer="homedepot",
            gap_type="complete_gap",
            dimension="size",
            dimension_value="10 in.",
            competitors_count=3,
            competitor_examples=["[walmart] IRWIN 10in ($15.98)"],
            priority_score=8.5,
            recommendation="建议开发10寸产品",
        )
        db_session.add(gap)
        db_session.commit()

        result = db_session.query(GapAnalysis).first()
        assert result.target_retailer == "homedepot"
        assert result.priority_score == 8.5
        assert len(result.competitor_examples) == 1

    def test_cascade_delete_from_task(self, db_session):
        task = ScrapeTask(category="plier")
        db_session.add(task)
        db_session.commit()

        gap = GapAnalysis(
            task_id=task.id,
            target_retailer="walmart",
            gap_type="brand_gap",
            dimension="brand",
            dimension_value="Knipex",
            competitors_count=2,
        )
        db_session.add(gap)
        db_session.commit()

        db_session.delete(task)
        db_session.commit()

        count = db_session.query(GapAnalysis).count()
        assert count == 0

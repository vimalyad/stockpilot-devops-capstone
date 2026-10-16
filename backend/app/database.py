import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://stockpilot:local-demo-only@localhost:5432/stockpilot",
)
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("postgresql"):
    # Bound connections per process so API autoscaling and Celery prefork workers
    # cannot each allocate an unbounded slice of PostgreSQL's connection budget.
    engine_options.update(
        pool_size=int(os.getenv("DB_POOL_SIZE", "3")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "2")),
        pool_timeout=10,
        pool_recycle=1800,
        connect_args={"connect_timeout": 5},
    )
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session

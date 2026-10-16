import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import OperationalError

from app import main, seed, tasks
from app.models import Movement, Product


def test_readiness_checks_database(client, database, monkeypatch):
    monkeypatch.setattr(main, "engine", database[0])
    assert client.get("/ready").json() == {"status": "ready"}
    offline = Mock()
    offline.connect.side_effect = OperationalError("SELECT 1", {}, Exception("offline"))
    monkeypatch.setattr(main, "engine", offline)
    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 200


def test_root_and_release_identity(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "a" * 40)
    assert client.get("/").json()["docs"] == "/docs"
    assert client.get("/api/meta").json()["version"] == "a" * 40


def test_background_report_and_missing_cache(client, catalog, database, monkeypatch):
    cache = Mock()
    monkeypatch.setattr(tasks, "SessionLocal", database[1])
    monkeypatch.setattr(tasks, "redis_client", lambda: cache)
    report = tasks.refresh_report.run()
    assert report["product_count"] == 1
    assert report["generated_at"]
    args = cache.setex.call_args.args
    assert args[0:2] == ("stockpilot:inventory-report", 180)
    monkeypatch.setattr(main, "redis_client", lambda: cache)
    cache.get.return_value = args[2]
    assert client.get("/api/reports/latest").json()["product_count"] == 1
    cache.get.return_value = None
    assert client.get("/api/reports/latest").status_code == 404


def test_demo_seed_is_repeatable(database, monkeypatch):
    monkeypatch.setattr(seed, "SessionLocal", database[1])
    seed.seed()
    seed.seed()
    with database[1]() as db:
        assert len(db.scalars(select(Product)).all()) == 8
        assert len(db.scalars(select(Movement)).all()) == 16


def test_alembic_upgrade_downgrade_round_trip(tmp_path):
    url = f"sqlite:///{tmp_path / 'migration-check.db'}"
    env = os.environ | {"DATABASE_URL": url}
    backend = Path(__file__).resolve().parents[1]
    for command in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"]):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *command],
            cwd=backend,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
    engine = create_engine(url)
    try:
        names = inspect(engine).get_table_names()
        assert {"products", "balances", "movements", "reservations", "purchase_orders", "order_lines"} <= set(
            names
        )
    finally:
        engine.dispose()

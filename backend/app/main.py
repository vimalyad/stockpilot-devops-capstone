import json
import logging
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from kombu.exceptions import OperationalError
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from . import catalog, inventory, orders
from .catalog import DB
from .database import engine
from .reporting import snapshot
from .tasks import redis_client, refresh_report

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("stockpilot")


def create_app():
    app = FastAPI(title="StockPilot API", version="1.0.0", description="Inventory, procurement and warehouse operations")
    registry = CollectorRegistry()
    requests = Counter("stockpilot_http_requests_total", "Completed HTTP requests", ["method", "route", "status"], registry=registry)
    latency = Histogram("stockpilot_http_request_duration_seconds", "HTTP duration", ["method", "route"], registry=registry)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        route = getattr(request.scope.get("route"), "path", "unmatched")
        elapsed = time.perf_counter() - started
        if route != "/metrics":
            requests.labels(request.method, route, response.status_code).inc()
            latency.labels(request.method, route).observe(elapsed)
            log.info(json.dumps({"method": request.method, "route": route, "status": response.status_code, "duration_ms": round(elapsed * 1000, 2)}))
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(IntegrityError)
    async def conflict(_request, _exception):
        return JSONResponse(status_code=409, content={"detail": "Record conflicts with an existing value or referenced inventory history"})

    @app.get("/")
    def root():
        return {"service": "StockPilot", "docs": "/docs"}

    @app.get("/health", tags=["Operations"])
    def health():
        return {"status": "ok"}

    @app.get("/ready", tags=["Operations"])
    def ready():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError:
            raise HTTPException(503, "Database unavailable") from None
        return {"status": "ready"}

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST})

    @app.get("/api/meta", tags=["Operations"])
    def meta():
        return {"name": "StockPilot", "version": os.getenv("APP_VERSION", "development")}

    @app.get("/api/dashboard", tags=["Reports"])
    def dashboard(db: DB):
        return snapshot(db)

    @app.post("/api/reports", status_code=202, tags=["Reports"])
    def request_report():
        try:
            task = refresh_report.delay()
        except (OperationalError, RedisError):
            raise HTTPException(503, "Background processing is unavailable; live inventory remains accessible") from None
        return {"task_id": task.id, "status": "queued"}

    @app.get("/api/reports/latest", tags=["Reports"])
    def latest_report():
        try:
            result = redis_client().get("stockpilot:inventory-report")
        except RedisError:
            raise HTTPException(503, "Report cache unavailable") from None
        if result is None:
            raise HTTPException(404, "No recent report; request one or wait for the scheduler")
        return json.loads(result)

    app.include_router(catalog.router)
    app.include_router(inventory.router)
    app.include_router(orders.router)
    return app


app = create_app()


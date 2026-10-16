import asyncio
import os
from contextlib import suppress
from functools import partial

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite://")

import httpx
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import create_app


@pytest.fixture()
def database():
    url = os.environ["DATABASE_URL"]
    if url.startswith("sqlite"):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
    else:
        # TEST_DATABASE_URL must identify a dedicated disposable database.
        if os.getenv("ALLOW_TEST_DATABASE_RESET") != "yes":
            pytest.fail("Set ALLOW_TEST_DATABASE_RESET=yes for the dedicated test database")
        engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield engine, factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(database):
    _engine, factory = database
    app = create_app()

    def session():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = session

    class InProcessClient:
        """Exercise HTTP validation and routing using ASGI, without a listening socket."""

        def request(self, method, url, **kwargs):
            async def run():
                # A timer also wakes callbacks in environments that restrict socketpair
                # notifications. Requests still pass through the real ASGI application.
                async def ticker():
                    while True:
                        await asyncio.sleep(0.01)

                wakeup = asyncio.create_task(ticker())
                try:
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app), base_url="http://test"
                    ) as http:
                        return await http.request(method, url, **kwargs)
                finally:
                    wakeup.cancel()
                    with suppress(asyncio.CancelledError):
                        await wakeup

            return asyncio.run(run())

        def __getattr__(self, method):
            return partial(self.request, method.upper())

    yield InProcessClient()


@pytest.fixture()
def catalog(client):
    supplier = client.post("/api/suppliers", json={"name": "Test supplier", "lead_days": 2}).json()
    warehouses = [
        client.post("/api/warehouses", json={"code": code, "name": code, "location": "Test"}).json()
        for code in ("WH-A", "WH-B")
    ]
    product = client.post(
        "/api/products",
        json={
            "sku": "TEST-01",
            "name": "Test product",
            "price_cents": 1200,
            "reorder_point": 5,
            "supplier_id": supplier["id"],
        },
    ).json()
    return {"supplier": supplier, "warehouses": warehouses, "product": product}

import pytest
from sqlalchemy import select

from app.models import Balance


def movement(catalog, **changes):
    return {
        "product_id": catalog["product"]["id"],
        "warehouse_id": catalog["warehouses"][0]["id"],
        "kind": "receipt",
        "quantity": 20,
        "idempotency_key": "receipt-test-01",
    } | changes


def test_receipt_retries_and_payload_mismatch(client, catalog):
    data = movement(catalog)
    first = client.post("/api/movements", json=data)
    second = client.post("/api/movements", json=data)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert client.get("/api/inventory").json()[0]["on_hand"] == 20
    assert client.post("/api/movements", json=data | {"quantity": 30}).status_code == 409


def test_transfer_preserves_total_stock(client, catalog):
    client.post("/api/movements", json=movement(catalog))
    data = movement(
        catalog,
        kind="transfer",
        destination_id=catalog["warehouses"][1]["id"],
        quantity=7,
        idempotency_key="transfer-test-01",
    )
    assert client.post("/api/movements", json=data).status_code == 201
    balances = client.get("/api/inventory").json()
    assert sorted(b["on_hand"] for b in balances) == [7, 13]
    assert sum(b["on_hand"] for b in balances) == 20


def test_failed_transfer_rolls_back_source(client, catalog):
    client.post("/api/movements", json=movement(catalog))
    response = client.post(
        "/api/movements",
        json=movement(catalog, kind="transfer", destination_id=999, idempotency_key="missing-destination"),
    )
    assert response.status_code == 404
    assert client.get("/api/inventory").json()[0]["on_hand"] == 20
    assert len(client.get("/api/movements").json()) == 1


@pytest.mark.parametrize(
    "change",
    [{"quantity": 0}, {"quantity": -5}, {"kind": "magic"}, {"kind": "transfer"}, {"destination_id": 2}],
)
def test_invalid_movements(client, catalog, change):
    assert client.post("/api/movements", json=movement(catalog, **change)).status_code == 422


def test_reservation_protects_stock_and_release_is_idempotent(client, catalog):
    client.post("/api/movements", json=movement(catalog))
    data = {
        "product_id": catalog["product"]["id"],
        "warehouse_id": catalog["warehouses"][0]["id"],
        "quantity": 15,
        "reference": "ORDER-1",
        "idempotency_key": "reserve-test-01",
    }
    created = client.post("/api/reservations", json=data)
    assert created.status_code == 201
    assert client.post("/api/reservations", json=data).json()["id"] == created.json()["id"]
    issue = movement(catalog, kind="issue", quantity=6, idempotency_key="issue-reserved-01")
    assert client.post("/api/movements", json=issue).status_code == 409
    uri = f"/api/reservations/{created.json()['id']}/release"
    assert client.post(uri).status_code == client.post(uri).status_code == 200
    assert client.get("/api/inventory").json()[0]["reserved"] == 0
    assert client.post("/api/movements", json=issue).status_code == 201


def test_fulfillment_deducts_once(client, catalog):
    client.post("/api/movements", json=movement(catalog))
    reserved = client.post(
        "/api/reservations",
        json={
            "product_id": catalog["product"]["id"],
            "warehouse_id": catalog["warehouses"][0]["id"],
            "quantity": 12,
            "reference": "SALE-01",
            "idempotency_key": "reserve-sale-01",
        },
    ).json()
    uri = f"/api/reservations/{reserved['id']}"
    assert client.post(uri + "/fulfill").status_code == 200
    assert client.post(uri + "/fulfill").status_code == 200
    assert client.post(uri + "/release").status_code == 409
    stock = client.get("/api/inventory").json()[0]
    assert (stock["on_hand"], stock["reserved"], stock["available"]) == (8, 0, 8)


def test_history_cannot_be_deleted(client, catalog):
    client.post("/api/movements", json=movement(catalog))
    assert client.delete(f"/api/products/{catalog['product']['id']}").status_code == 409


def test_dashboard_includes_zero_stock_and_valuation(client, catalog):
    assert client.get("/api/dashboard").json()["low_stock"][0]["available"] == 0
    client.post("/api/movements", json=movement(catalog))
    report = client.get("/api/dashboard").json()
    assert report["on_hand"] == 20
    assert report["inventory_value_cents"] == 24000
    assert report["low_stock"] == []


@pytest.mark.postgres
def test_concurrent_issues_cannot_oversell(client, catalog, database):
    from concurrent.futures import ThreadPoolExecutor

    from fastapi import HTTPException

    from app.inventory import apply_movement
    from app.schemas import MovementIn

    engine, factory = database
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires a PostgreSQL test database for row locks")
    client.post("/api/movements", json=movement(catalog, quantity=10))

    def issue(index):
        with factory() as db:
            try:
                apply_movement(
                    db,
                    MovementIn(
                        **movement(
                            catalog, kind="issue", quantity=8, idempotency_key=f"concurrent-issue-{index}"
                        )
                    ),
                )
                db.commit()
                return 201
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(issue, range(2))) == [201, 409]
    with factory() as db:
        assert db.scalar(select(Balance.on_hand)) == 2
